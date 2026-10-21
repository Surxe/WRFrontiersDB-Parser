"""Bake an exported scene into a mesh library plus an instance list.

A map is tens of millions of triangles once every placement is expanded, but
only a few million unique ones: the same crate, fence or wall is placed
thousands of times. The bake keeps that structure: each unique mesh once, in its
own local space, plus an instance list (which mesh, where, owned by which actor,
with flags saying how it takes part in a match). The cook (``cook.py``) writes it
out as instanced glTF.

The geometry is the triangles the game draws: LOD0 of each mesh (the Nanite
fallback mesh), the landscape triangulated from its height grid, and brushes as
their convex hulls.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .scene import ALWAYS_KINDS, DYNAMIC_KIND, INSTANCE_KIND, Scene, instance_matrix, transform_matrix
from .ueformat import UEFormatError, read_uemodel

# Instance kinds, stored in ``inst_kind``.
KIND_STATIC_MESH = 0
KIND_INSTANCED_MESH = 1
KIND_SPLINE_MESH = 2
KIND_BRUSH = 3
KIND_LANDSCAPE = 4
KIND_NAMES = ["static_mesh", "instanced_static_mesh", "spline_mesh", "brush", "landscape"]

# Bits of ``inst_flags``.
FLAG_HIDDEN = 1  # actor hidden, or component not visible / hidden in game
FLAG_NO_COLLISION = 2  # collision disabled on the component (or by the mesh default)
FLAG_DYNAMIC_LEVEL = 4  # in a dynamically loaded sublevel (game mode, lighting, ...)
FLAG_MAP_BOUNDARY = 8  # the wall that fences in the playable area
FLAG_MAP_CEILING = 16  # the invisible slab that caps the playable area

_NO_COLLISION = "NoCollision"
# The game's config (DefaultEngine.ini) names this trace channel "MapBoundariesWall"; the
# boundary wall is whatever has it as its collision object type.
_BOUNDARY_CHANNEL = "ECC_GameTraceChannel7"
# Not every map sets that channel, so the meshes the wall is built from count as well: the
# red-line wall laid along a landscape spline (SM_Fade, SM_Fade_02), a mesh modelled for one
# map (SM_EM1_MapBoundaries, SM_TortugaMapBorders, SM_FiringRangeBoundaries), and the
# collision-less outline a boundary volume was traced from (SM_GameplayBoard_Main).
_BOUNDARY_MESH_NAME = re.compile(r"^SM_Fade(_\d+)?$|(Boundaries|MapBorders)$|^SM_GameplayBoard")
_BLOCKING_VOLUME = "BlockingVolume"
# Houdini Engine's stand-in for an instance it couldn't resolve. The plugin's content isn't
# cooked into the game, so the game draws nothing there either: skipped without a warning.
_HOUDINI_PLACEHOLDER_PREFIX = "/HoudiniEngine/"
# Share of the navigation mesh's footprint a volume must span to count as enclosing the map.
_ENCLOSING_SHARE = 0.9


@dataclass
class _Library:
    """Unique meshes, concatenated: mesh ``i`` owns vertices
    ``[vertex_offset[i], vertex_offset[i + 1])`` and likewise for faces."""
    names: List[str] = field(default_factory=list)
    index: Dict[str, int] = field(default_factory=dict)
    vertices: List[np.ndarray] = field(default_factory=list)
    faces: List[np.ndarray] = field(default_factory=list)

    def add(self, name: str, vertices: np.ndarray, faces: np.ndarray) -> int:
        self.index[name] = len(self.names)
        self.names.append(name)
        self.vertices.append(np.asarray(vertices, dtype=np.float32).reshape(-1, 3))
        self.faces.append(np.asarray(faces, dtype=np.uint32).reshape(-1, 3))
        return self.index[name]


def _merge_parts(parts: List[Tuple[np.ndarray, np.ndarray]]) -> Tuple[np.ndarray, np.ndarray]:
    vertices, faces, offset = [], [], 0
    for part_vertices, part_faces in parts:
        if len(part_vertices) == 0 or len(part_faces) == 0:
            continue
        vertices.append(part_vertices)
        faces.append(np.asarray(part_faces) + offset)
        offset += len(part_vertices)
    if not vertices:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.uint32)
    return np.concatenate(vertices), np.concatenate(faces)


def _hull_parts(hulls: List[dict]) -> List[Tuple[np.ndarray, np.ndarray]]:
    parts = []
    for hull in hulls:
        vertices = np.asarray(hull["vertices"], dtype=float).reshape(-1, 3)
        indices = np.asarray(hull["indices"], dtype=np.int64)
        parts.append((vertices, indices[: len(indices) // 3 * 3].reshape(-1, 3)))
    return parts


def _landscape_mesh(scene: Scene, landscape: dict, stride: int) -> Tuple[np.ndarray, np.ndarray]:
    """Triangulate the height grid, one quad per ``stride`` grid cells, skipping
    the cells no landscape component covers."""
    width, height = landscape["width"], landscape["height"]
    heights = np.fromfile(scene.file(landscape["heightfield"]), dtype="<u2").reshape(height, width)

    size = landscape["component_size_quads"]
    covered = np.zeros((height, width), dtype=bool)
    for base_x, base_y in landscape["components"]:
        covered[base_y:base_y + size + 1, base_x:base_x + size + 1] = True

    columns = np.arange(0, width, stride)
    rows = np.arange(0, height, stride)
    grid_x, grid_y = np.meshgrid(columns, rows)
    local_z = (heights[np.ix_(rows, columns)].astype(np.float64) - landscape["z_offset"]) * landscape["z_scale"]
    origin_x, origin_y = landscape["origin"]
    vertices = np.stack([grid_x + origin_x, grid_y + origin_y, local_z], axis=-1).reshape(-1, 3)

    count_y, count_x = grid_x.shape
    index = np.arange(count_y * count_x).reshape(count_y, count_x)
    a, b, c, d = index[:-1, :-1], index[:-1, 1:], index[1:, :-1], index[1:, 1:]
    sampled = covered[np.ix_(rows, columns)]
    quad = (sampled[:-1, :-1] & sampled[:-1, 1:] & sampled[1:, :-1] & sampled[1:, 1:]).ravel()
    faces = np.concatenate([
        np.stack([a.ravel(), d.ravel(), b.ravel()], axis=1)[quad],
        np.stack([a.ravel(), c.ravel(), d.ravel()], axis=1)[quad],
    ])
    return vertices, faces


def _is_no_collision(component: dict, mesh_summary: Optional[dict]) -> bool:
    collision = component.get("collision") or {}
    if _NO_COLLISION in str(collision.get("enabled", "")) or collision.get("profile") == _NO_COLLISION:
        return True
    # A component that sets nothing itself takes the mesh's default collision.
    if "profile" not in collision and "enabled" not in collision and mesh_summary:
        return (mesh_summary.get("collision") or {}).get("default_profile") == _NO_COLLISION
    return False


def _is_map_boundary(component: dict) -> bool:
    object_type = str((component.get("collision") or {}).get("object_type", ""))
    mesh_name = (component.get("mesh") or "").rsplit(".", 1)[-1]
    return object_type.endswith(_BOUNDARY_CHANNEL) or bool(_BOUNDARY_MESH_NAME.search(mesh_name))


def enclosing_volume_flags(bounds: np.ndarray, hulls: np.ndarray, navmesh_low: np.ndarray,
                           navmesh_high: np.ndarray) -> np.ndarray:
    """Flags of the blocking volumes that enclose the whole map, from their shape alone.

    ``bounds`` are the (N, 2, 3) world boxes of blocking volumes and ``hulls`` how many
    convex pieces each is made of. A volume spanning the navigation mesh is one of two
    things. In one piece and over it, it is the ceiling. In several pieces and level
    with it, it has to be hollow, since a solid one would leave no room to stand in: it
    is a wall around the map.

    "Over" is measured against the middle of the navigation mesh's height range, not its
    top: the navmesh build treats the ceiling as ground, so stray polygons lie on top of it.
    """
    flags = np.zeros(len(bounds), dtype=np.uint8)
    if not len(bounds):
        return flags
    overlap = np.minimum(bounds[:, 1, :2], navmesh_high[:2]) - np.maximum(bounds[:, 0, :2], navmesh_low[:2])
    footprint = np.prod(navmesh_high[:2] - navmesh_low[:2])
    spans = np.prod(np.clip(overlap, 0, None), axis=1) >= _ENCLOSING_SHARE * footprint
    above = bounds[:, 0, 2] >= (navmesh_low[2] + navmesh_high[2]) / 2
    flags[spans & (hulls == 1) & above] = FLAG_MAP_CEILING
    flags[spans & (hulls > 1) & ~above] = FLAG_MAP_BOUNDARY
    return flags


class _MeshSource:
    """Loads each mesh's LOD0 into the library once."""

    def __init__(self, scene: Scene, library: _Library, warnings: List[str]) -> None:
        self.scene = scene
        self.library = library
        self.warnings = warnings
        self.failed: set = set()

    def _render(self, model_file: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        try:
            model = read_uemodel(self.scene.file(model_file))
        except (OSError, UEFormatError) as error:
            self.warnings.append(f"{model_file}: {error}")
            return None
        if not model.lods:
            return None
        return model.lods[0].vertices, model.lods[0].indices

    def static_mesh(self, mesh_path: str) -> Optional[int]:
        if mesh_path in self.library.index:
            return self.library.index[mesh_path]
        if mesh_path in self.failed:
            return None

        if mesh_path.startswith(_HOUDINI_PLACEHOLDER_PREFIX):
            return None
        summary = self.scene.meshes.get(mesh_path) or {}
        mesh = self._render(summary["model"]) if summary.get("model") else None
        if mesh is None or len(mesh[1]) == 0:
            self.failed.add(mesh_path)
            return None
        return self.library.add(mesh_path, mesh[0], mesh[1])

    def model_file(self, model_file: str) -> Optional[int]:
        mesh = self._render(model_file)
        if mesh is None or len(mesh[1]) == 0:
            return None
        return self.library.add(model_file, mesh[0], mesh[1])


def bake(scene: Scene, landscape_stride: int = 4) -> dict:
    """Build the mesh library and instance list of a scene.

    | Key | Shape | Content |
    |-----|-------|---------|
    | ``mesh_vertices`` | (V, 3) float32 | Vertices of all library meshes, concatenated, local space |
    | ``mesh_faces`` | (F, 3) uint32 | Triangles, indices local to their mesh |
    | ``mesh_vertex_offset``, ``mesh_face_offset`` | (M+1,) int64 | Mesh ``i`` owns ``[offset[i], offset[i+1])`` |
    | ``mesh_names`` | list of M str | Mesh asset path (or model file, brush, height grid) of each library mesh |
    | ``inst_mesh`` | (I,) int32 | Library mesh of each instance |
    | ``inst_matrix`` | (I, 4, 4) float64 | Local to world: ``world = M @ [x, y, z, 1]`` |
    | ``inst_aabb`` | (I, 2, 3) float64 | World-space min/max box of each instance |
    | ``inst_actor``, ``inst_level`` | (I,) int32 | Owning actor id and level index |
    | ``inst_kind`` | (I,) uint8 | ``KIND_*`` |
    | ``inst_flags`` | (I,) uint8 | ``FLAG_*`` bits |
    | ``levels`` | list | The scene's levels: index, name, kind, parent |
    | ``warnings`` | list of str | Meshes that could not be read |

    Units are Unreal's: centimeters, left-handed, +Z up.
    """
    library = _Library()
    warnings: List[str] = []
    source = _MeshSource(scene, library, warnings)

    dynamic = np.array([scene.streaming_root(level["index"])["kind"] == DYNAMIC_KIND for level in scene.levels])
    inst_mesh, inst_matrix, inst_actor, inst_level, inst_kind, inst_flags = [], [], [], [], [], []
    # Convex pieces of each blocking volume, by instance: what tells a wall from a slab.
    volume_hulls: Dict[int, int] = {}
    navmesh_actors = []

    def add_instance(mesh: Optional[int], matrix: np.ndarray, actor: dict, kind: int, flags: int) -> None:
        if mesh is None:
            return
        inst_mesh.append(mesh)
        inst_matrix.append(matrix)
        inst_actor.append(actor["id"])
        inst_level.append(actor["level"])
        inst_kind.append(kind)
        inst_flags.append(flags | (FLAG_DYNAMIC_LEVEL if dynamic[actor["level"]] else 0))

    for actor in scene.actors():
        actor_flags = FLAG_HIDDEN if actor.get("hidden") else 0
        if "navmesh" in actor:
            navmesh_actors.append(actor)

        if "landscape" in actor:
            name = actor["landscape"]["heightfield"]
            vertices, faces = _landscape_mesh(scene, actor["landscape"], landscape_stride)
            if len(faces):
                add_instance(library.add(name, vertices, faces), transform_matrix(actor["world"]), actor, KIND_LANDSCAPE, actor_flags)

        for component in actor["components"]:
            kind = component["kind"]
            if kind not in ("static_mesh", "instanced_static_mesh", "spline_mesh", "brush"):
                continue

            flags = actor_flags
            if component.get("visible") is False or component.get("hidden_in_game"):
                flags |= FLAG_HIDDEN
            if _is_no_collision(component, scene.meshes.get(component.get("mesh") or "")):
                flags |= FLAG_NO_COLLISION
            if _is_map_boundary(component):
                flags |= FLAG_MAP_BOUNDARY
            world = transform_matrix(component["world"])

            if kind == "brush":
                vertices, faces = _merge_parts(_hull_parts(component.get("convex", [])))
                if len(faces):
                    name = f"brush:{actor['id']}:{component['name']}"
                    if _BLOCKING_VOLUME in actor.get("class_chain", ()):
                        volume_hulls[len(inst_mesh)] = len(component["convex"])
                    add_instance(library.add(name, vertices, faces), world, actor, KIND_BRUSH, flags)
            elif kind == "spline_mesh":
                # Already deformed along its spline at export time, so each one is unique.
                if component.get("model"):
                    add_instance(source.model_file(component["model"]), world, actor, KIND_SPLINE_MESH, flags)
            elif component.get("mesh"):
                mesh = source.static_mesh(component["mesh"])
                if kind == "static_mesh":
                    add_instance(mesh, world, actor, KIND_STATIC_MESH, flags)
                else:
                    for instance in component.get("instances", []):
                        add_instance(mesh, instance_matrix(instance), actor, KIND_INSTANCED_MESH, flags)

    for mesh_path in sorted(source.failed):
        warnings.append(f"{mesh_path}: no geometry")

    vertex_counts = [len(vertices) for vertices in library.vertices]
    face_counts = [len(faces) for faces in library.faces]
    mesh_vertices = np.concatenate(library.vertices) if library.vertices else np.zeros((0, 3), dtype=np.float32)
    mesh_faces = np.concatenate(library.faces) if library.faces else np.zeros((0, 3), dtype=np.uint32)
    vertex_offset = np.concatenate([[0], np.cumsum(vertex_counts)]).astype(np.int64)
    face_offset = np.concatenate([[0], np.cumsum(face_counts)]).astype(np.int64)

    matrices = np.array(inst_matrix, dtype=np.float64).reshape(-1, 4, 4)
    meshes = np.array(inst_mesh, dtype=np.int32)
    flags = np.array(inst_flags, dtype=np.uint8)
    bounds = instance_bounds(mesh_vertices, vertex_offset, meshes, matrices)

    navmesh = scene.navmesh_bounds(navmesh_actors)
    if navmesh is not None and volume_hulls:
        volumes = np.fromiter(volume_hulls, dtype=np.int64)
        hulls = np.fromiter(volume_hulls.values(), dtype=np.int64)
        flags[volumes] |= enclosing_volume_flags(bounds[volumes], hulls, *navmesh)

    return {
        "mesh_vertices": mesh_vertices,
        "mesh_faces": mesh_faces,
        "mesh_vertex_offset": vertex_offset,
        "mesh_face_offset": face_offset,
        "mesh_names": library.names,
        "inst_mesh": meshes,
        "inst_matrix": matrices,
        "inst_actor": np.array(inst_actor, dtype=np.int32),
        "inst_level": np.array(inst_level, dtype=np.int32),
        "inst_kind": np.array(inst_kind, dtype=np.uint8),
        "inst_flags": flags,
        "inst_aabb": bounds,
        "levels": [
            {"index": level["index"], "name": level["name"], "kind": level["kind"], "parent": level.get("parent")}
            for level in scene.levels
        ],
        "navmesh": navmesh,
        "warnings": warnings,
    }


def boundary_mask(baked: dict) -> np.ndarray:
    """The boundary wall as it stands in every match: flagged, colliding, always loaded."""
    flags = baked["inst_flags"]
    return (flags & FLAG_MAP_BOUNDARY != 0) & (flags & (FLAG_NO_COLLISION | FLAG_DYNAMIC_LEVEL) == 0)


def instance_bounds(mesh_vertices, vertex_offset, inst_mesh, inst_matrix) -> np.ndarray:
    """World-space axis-aligned box of every instance, as (I, 2, 3) min/max."""
    count = len(vertex_offset) - 1
    corners = np.zeros((count, 8, 3))
    for mesh in range(count):
        vertices = mesh_vertices[vertex_offset[mesh]:vertex_offset[mesh + 1]]
        low, high = vertices.min(axis=0), vertices.max(axis=0)
        corners[mesh] = [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]

    bounds = np.zeros((len(inst_mesh), 2, 3))
    if len(inst_mesh):
        world = np.einsum("nij,nkj->nki", inst_matrix[:, :3, :3], corners[inst_mesh]) + inst_matrix[:, None, :3, 3]
        bounds[:, 0] = world.min(axis=1)
        bounds[:, 1] = world.max(axis=1)
    return bounds


def streaming_roots(baked: dict) -> List[dict]:
    """Per level index, the streaming sublevel (or persistent level) it belongs to: itself,
    or for a level instance the level its chain of instances is placed in."""
    levels = baked["levels"]

    def root(level: dict) -> dict:
        while level["kind"] == INSTANCE_KIND:
            level = levels[level["parent"]]
        return level

    return [root(level) for level in levels]


def level_mask(baked: dict, dynamic_levels=()) -> np.ndarray:
    """Instances present when only the always-loaded sublevels and the named
    dynamic ones (e.g. ``["Mont_Spearhead"]``) are loaded."""
    wanted = set(dynamic_levels)
    active = np.array([root["kind"] in ALWAYS_KINDS or root["name"] in wanted for root in streaming_roots(baked)],
                      dtype=bool)
    return active[baked["inst_level"]]
