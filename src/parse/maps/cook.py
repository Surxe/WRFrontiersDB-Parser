"""Cook one exported map into the files the Site's map viewer loads.

Input: the map export (``<export>/maps/<Map>/`` from BatchExport's map mode). Output,
under ``Maps/`` in the parser's output:

| File | Content |
|------|---------|
| ``<Map>.glb`` | The map as every match has it: the always-loaded levels, drawn instances only (no hidden ones, boundary wall, ceiling or brushes), cut to the instances touching the playable box, without foliage |
| ``<Map>.foliage.glb`` | The foliage: no-collision instances of meshes under ``/Environment/Foliage/`` (trees, bushes, grass), simplified hard. Tens of millions of triangles on the jungle maps, so the Site toggles it |
| ``<Map>.<Mode>.glb`` | Geometry a game mode adds: the drawn instances in the sublevels it loads visibly (Mont's ``_Crusher``). Only written when not empty |
| ``<Map>.json`` | Per mode, the pins (spawns, beacons, probes, power-ups, ...) slimmed from ``objectives.extract``, plus the file list and the input hash |

The GLBs hold render geometry (LOD0) with normals, untextured: each unique mesh once and
one node per instance, which gltfpack turns into ``EXT_mesh_gpu_instancing`` and meshopt
compression. Positions stay float (``-vpf``): gltfpack merges single-use meshes into world
space, where quantization errors reached 6551% of a mesh. glTF axes: meters, +Y up,
right-handed; an Unreal point (x, y, z) in cm is at (x, z, y) / 100. Pins stay in Unreal
units (centimeters, +Z up, yaw 0 = +X).

A map whose input is unchanged (same hash of its export, the meshes it uses and this
cook's settings) is copied from the cache instead of cooked again, so unchanged maps
stay byte-identical in the data repo.
"""
import hashlib
import json
import shutil
import struct
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from loguru import logger

from . import bake as baking
from .gltfpack import GLTFPACK_VERSION, run_gltfpack
from .objectives import extract
from .scene import Scene

# Bump on any change to what the cook writes, so cached maps are cooked again.
COOK_VERSION = 1
PACK_OPTIONS = ["-cc", "-mi", "-vpf"]
FOLIAGE_PATH = "/Environment/Foliage/"
# Foliage meshes are up to 2,500 triangles at LOD0 and placed tens of thousands of times
# (CrashSite: 128M triangles drawn). Leaves are loose cards, which gltfpack's default 1%
# error limit keeps almost whole (a 5% target still drew 68M); at 20% they go to ~6M.
FOLIAGE_PACK_OPTIONS = ["-si", "0.05", "-se", "0.2"]
# Share of the playable area's longer side kept around it.
MARGIN = 0.12
LANDSCAPE_STRIDE = 4
_NOT_DRAWN = baking.FLAG_HIDDEN | baking.FLAG_MAP_BOUNDARY | baking.FLAG_MAP_CEILING
# Component that carries the zone shown as a ring, by pin type.
ZONE_COMPONENTS = {"warp_probe": "CaptureZoneComponent", "beacon": "CaptureZoneComponent", "drill": "DamageZone"}
PIN_TYPES = ("spawn", "warp_probe", "beacon", "powerup_spawner", "ctf_core", "ctf_upload_zone", "drill")
UNITS = "centimeters, Unreal axes (left-handed, +Z up); yaw in degrees, 0 faces +X"

_GLB_MAGIC = 0x46546C67  # "glTF"
_JSON_CHUNK = 0x4E4F534A
_BINARY_CHUNK = 0x004E4942
_FLOAT, _UNSIGNED_INT = 5126, 5125
_ARRAY_BUFFER, _ELEMENT_ARRAY_BUFFER = 34962, 34963
# Unreal cm (x, y, z) -> glTF m (x, z, y). Swapping two axes is a reflection, so it also
# turns Unreal's left-handed space right-handed; triangle winding is reversed to match.
_TO_GLTF = np.array([[0.01, 0, 0, 0], [0, 0, 0.01, 0], [0, 0.01, 0, 0], [0, 0, 0, 1]])
_FROM_GLTF = np.linalg.inv(_TO_GLTF)


# ---------------- what goes where ----------------

def playable_box(baked: dict) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Box around the space a match is played in; None for a map without a navigation mesh.

    To the sides and below it is the navigation mesh with a margin. Its top is the map's
    ceiling where one was identified: nothing above it can be reached, and the navigation
    mesh is no guide there, having stray polygons on top of the ceiling itself.
    """
    if baked["navmesh"] is None:
        return None
    low, high = (np.array(corner, dtype=float) for corner in baked["navmesh"])
    pad = (high[:2] - low[:2]).max() * MARGIN
    ceilings = (baked["inst_flags"] & baking.FLAG_MAP_CEILING != 0) & baking.level_mask(baked)
    top = baked["inst_aabb"][ceilings, 0, 2].min() if ceilings.any() else high[2] + pad
    return np.array([low[0] - pad, low[1] - pad, low[2] - pad]), np.array([high[0] + pad, high[1] + pad, top])


def drawn_mask(baked: dict, box: Optional[Tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    """Instances drawn in a match (any level) that touch the playable box."""
    mask = ((baked["inst_flags"] & _NOT_DRAWN) == 0) & (baked["inst_kind"] != baking.KIND_BRUSH)
    if box is not None:
        aabb = baked["inst_aabb"]
        mask &= np.all(aabb[:, 1] >= box[0], axis=1) & np.all(aabb[:, 0] <= box[1], axis=1)
    return mask


def foliage_mask(baked: dict) -> np.ndarray:
    """Foliage: instances without collision of meshes under ``/Environment/Foliage/``.
    Robots walk through them, and on the jungle maps they are most of the triangles."""
    foliage_meshes = np.array([FOLIAGE_PATH in name for name in baked["mesh_names"]] + [False], dtype=bool)
    return foliage_meshes[baked["inst_mesh"]] & (baked["inst_flags"] & baking.FLAG_NO_COLLISION != 0)


def sublevel_mask(baked: dict, level_names: Iterable[str]) -> np.ndarray:
    """Instances in the named streaming sublevels (case-insensitive: the game's own level
    names are not consistent, e.g. ``Crashsite_MightyBushesNew``)."""
    wanted = {name.lower() for name in level_names}
    in_wanted = np.array([root["name"].lower() in wanted for root in baking.streaming_roots(baked)] + [False], dtype=bool)
    return in_wanted[baked["inst_level"]] if len(baked["inst_level"]) else np.zeros(0, dtype=bool)


def map_levels(map_name: str, suffixes: Iterable[str], scene_levels: Iterable[dict]) -> List[str]:
    """Names of the map's sublevels for the given suffixes (``Crusher`` -> ``Mont_Crusher``),
    as spelled in the scene; suffixes the map has no sublevel for are left out."""
    by_lower = {level["name"].lower(): level["name"] for level in scene_levels if not level.get("missing")}
    names = []
    for suffix in suffixes:
        name = by_lower.get(f"{map_name}_{suffix}".lower())
        if name:
            names.append(name)
    return names


# ---------------- glTF ----------------

def _vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals; (0, 1, 0) where a vertex has no area around it."""
    corners = vertices.astype(np.float64)[faces]
    face_normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals = np.zeros((len(vertices), 3))
    for corner in range(3):
        np.add.at(normals, faces[:, corner], face_normals)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return np.where(length > 0, normals / np.maximum(length, 1e-12), [0.0, 1.0, 0.0]).astype(np.float32)


def instanced_glb(baked: dict, mask: np.ndarray) -> Tuple[bytes, dict]:
    """A .glb of the selected instances: each library mesh they use once (positions and
    normals, glTF axes), one node per instance. Returns the file and counts."""
    vertex_offset, face_offset = baked["mesh_vertex_offset"], baked["mesh_face_offset"]
    selected = np.flatnonzero(mask)
    selected = selected[(face_offset[baked["inst_mesh"][selected] + 1] - face_offset[baked["inst_mesh"][selected]]) > 0]
    used = np.unique(baked["inst_mesh"][selected])

    blob = bytearray()
    buffer_views, accessors, meshes = [], [], []

    def add_view(data: bytes, target: int) -> int:
        blob.extend(b"\0" * (-len(blob) % 4))
        buffer_views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(buffer_views) - 1

    mesh_index = {}
    for mesh in used:
        local = baked["mesh_vertices"][vertex_offset[mesh]:vertex_offset[mesh + 1]].astype(np.float64)
        vertices = (local[:, [0, 2, 1]] * 0.01).astype(np.float32)
        faces = baked["mesh_faces"][face_offset[mesh]:face_offset[mesh + 1]][:, [0, 2, 1]].astype(np.uint32)
        normals = _vertex_normals(vertices, faces)
        first = len(accessors)
        accessors += [
            {"bufferView": add_view(vertices.tobytes(), _ARRAY_BUFFER), "componentType": _FLOAT, "count": len(vertices),
             "type": "VEC3", "min": vertices.min(axis=0).tolist(), "max": vertices.max(axis=0).tolist()},
            {"bufferView": add_view(normals.tobytes(), _ARRAY_BUFFER), "componentType": _FLOAT, "count": len(normals),
             "type": "VEC3"},
            {"bufferView": add_view(faces.tobytes(), _ELEMENT_ARRAY_BUFFER), "componentType": _UNSIGNED_INT,
             "count": faces.size, "type": "SCALAR"},
        ]
        meshes.append({"primitives": [{"attributes": {"POSITION": first, "NORMAL": first + 1}, "indices": first + 2,
                                       "material": 0}]})
        mesh_index[int(mesh)] = len(meshes) - 1

    nodes = []
    for instance in selected:
        matrix = _TO_GLTF @ baked["inst_matrix"][instance] @ _FROM_GLTF
        nodes.append({"mesh": mesh_index[int(baked["inst_mesh"][instance])], "matrix": matrix.T.reshape(-1).tolist()})

    document = {
        "asset": {"version": "2.0", "generator": "WRFrontiersDB-Parser map cook"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [{"doubleSided": True, "pbrMetallicRoughness": {
            "baseColorFactor": [0.7, 0.7, 0.7, 1], "metallicFactor": 0, "roughnessFactor": 0.9}}],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob)}],
    }
    face_counts = face_offset[baked["inst_mesh"][selected] + 1] - face_offset[baked["inst_mesh"][selected]]
    counts = {
        "instances": len(nodes),
        "unique_meshes": len(used),
        "unique_triangles": int((face_offset[used + 1] - face_offset[used]).sum()),
        "triangles": int(face_counts.sum()),
    }
    return _glb(document, bytes(blob)), counts


def _glb(document: dict, binary: bytes) -> bytes:
    json_bytes = json.dumps(document, separators=(",", ":")).encode()
    json_bytes += b" " * (-len(json_bytes) % 4)
    binary += b"\0" * (-len(binary) % 4)
    return b"".join([
        struct.pack("<III", _GLB_MAGIC, 2, 12 + 8 + len(json_bytes) + 8 + len(binary)),
        struct.pack("<II", len(json_bytes), _JSON_CHUNK), json_bytes,
        struct.pack("<II", len(binary), _BINARY_CHUNK), binary,
    ])


def glb_document(glb_file: Path) -> dict:
    """The JSON chunk of a .glb."""
    with open(glb_file, "rb") as source:
        header = source.read(20)
        json_length, chunk_type = struct.unpack_from("<II", header, 12)
        if chunk_type != _JSON_CHUNK:
            raise ValueError(f"{glb_file}: no JSON chunk first")
        return json.loads(source.read(json_length))


def glb_triangles(glb_file: Path) -> Tuple[int, int]:
    """(unique, drawn) triangle counts of a .glb, counting EXT_mesh_gpu_instancing copies."""
    document = glb_document(glb_file)
    accessors = document.get("accessors", [])
    mesh_triangles = [sum(accessors[primitive["indices"]]["count"] // 3 for primitive in mesh["primitives"])
                      for mesh in document.get("meshes", [])]
    drawn = 0
    for node in document.get("nodes", []):
        if "mesh" not in node:
            continue
        instancing = node.get("extensions", {}).get("EXT_mesh_gpu_instancing")
        copies = accessors[next(iter(instancing["attributes"].values()))]["count"] if instancing else 1
        drawn += mesh_triangles[node["mesh"]] * copies
    return sum(mesh_triangles), drawn


def _pack(baked: dict, mask: np.ndarray, glb_file: Path, gltfpack_cmd: Path, work_dir: Path,
          extra_options: List[str] = ()) -> Optional[dict]:
    """Write the selected instances to ``glb_file`` through gltfpack; None (nothing written)
    when nothing is selected."""
    if not mask.any():
        return None
    raw, counts = instanced_glb(baked, mask)
    if counts["instances"] == 0:
        return None
    raw_file = work_dir / f"{glb_file.stem}.raw.glb"
    raw_file.write_bytes(raw)
    del raw
    output = run_gltfpack(gltfpack_cmd, raw_file, glb_file, PACK_OPTIONS + list(extra_options))
    raw_file.unlink()
    for line in output.splitlines():
        if "warning" in line.lower():
            logger.warning(f"gltfpack {glb_file.name}: {line}")
    unique, drawn = glb_triangles(glb_file)
    counts.update({"packed_unique_triangles": unique, "packed_triangles": drawn, "bytes": glb_file.stat().st_size})
    return counts


# ---------------- pins ----------------

def _team(point: dict) -> Optional[int]:
    if point.get("team") is not None:
        return point["team"]
    owning = point["props"].get("OwningTeamId")
    return owning.get("TeamId") if isinstance(owning, dict) else None


def _zone_radius(point: dict) -> Optional[float]:
    wanted = ZONE_COMPONENTS.get(point["type"])
    for zone in point["zones"]:
        if zone["component"] == wanted and "half_extent" in zone:
            return round(float(max(zone["half_extent"][0], zone["half_extent"][1])), 1)
    return None


def _powerup_ids(point: dict) -> List[str]:
    """Power-ups a spawner spawns, as Powerup ids (the spawned Blueprint's asset name)."""
    ids = []
    for entry in point["props"].get("SpawnableActors") or []:
        path = ((entry or {}).get("SpawnableActor") or {}).get("ObjectPath") or ""
        name = path.rsplit("/", 1)[-1].split(".", 1)[0]
        if name and name not in ids:
            ids.append(name)
    return ids


def slim_point(point: dict) -> dict:
    """A gameplay object as the Site draws it."""
    pin = {"type": point["type"]}
    team = _team(point)
    if team is not None:
        pin["team"] = team
    pin["position"] = [round(float(value), 1) for value in point["position"]]
    pin["yaw"] = round(float(point["yaw_degrees"]), 1)
    order = point["props"].get("Order", point["props"].get("DisplayOrder"))
    if point["type"] in ("warp_probe", "beacon") and isinstance(order, int):
        pin["order"] = order
    radius = _zone_radius(point)
    if radius is not None:
        pin["zone_radius"] = radius
    if point["type"] == "powerup_spawner":
        pin["powerup_ids"] = _powerup_ids(point)
    return pin


def mode_pins(objectives: dict, levels: Iterable[str]) -> List[dict]:
    """Pins of the objects in the given sublevels (a mode's own and the shared ones it loads)."""
    by_level = {entry["level"].lower(): entry for entry in objectives["modes"].values()}
    pins = []
    for level in levels:
        entry = by_level.get(level.lower())
        if entry:
            pins += [slim_point(point) for point in entry["points"] if point["type"] in PIN_TYPES]
    return pins


# ---------------- input hash + cache ----------------

def _hash_file(digest, file: Path) -> None:
    with open(file, "rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)


def input_hash(scene: Scene, settings: dict) -> str:
    """Hash of everything a cook reads: the map's export (less the export time), the mesh
    files its scene refers to, and the cook's own settings."""
    digest = hashlib.sha256()
    digest.update(json.dumps(settings, sort_keys=True).encode())
    data = {key: value for key, value in scene.data.items() if key != "exported_utc"}
    digest.update(json.dumps(data, sort_keys=True).encode())

    files = {path for path in scene.map_dir.rglob("*") if path.is_file() and path.name != "scene.json"}
    for mesh in scene.meshes.values():
        for key in ("model", "info"):
            if mesh.get(key):
                files.add(scene.file(mesh[key]))
    for file in sorted(files):
        digest.update(str(file.relative_to(scene.export_dir)).encode())
        if file.is_file():
            _hash_file(digest, file)
    return digest.hexdigest()


def pins_file_name(map_name: str) -> str:
    return f"{map_name}.json"


def cooked_files(pins: dict) -> List[str]:
    """Every file a cook wrote, the pins file included."""
    files = [pins_file_name(pins["map"]), pins["files"]["base"], pins["files"]["foliage"]]
    files += [mode["file"] for mode in pins["modes"].values()]
    return [file for file in files if file]


def _cached(cache_dir: Optional[Path], map_name: str, digest: str) -> Optional[dict]:
    """The cached cook of a map if its input hash matches and all its files are there."""
    if cache_dir is None:
        return None
    pins_file = cache_dir / map_name / pins_file_name(map_name)
    if not pins_file.is_file():
        return None
    try:
        pins = json.loads(pins_file.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if pins.get("input_hash") != digest or pins.get("version") != COOK_VERSION:
        return None
    if not all((cache_dir / map_name / file).is_file() for file in cooked_files(pins)):
        return None
    return pins


def _copy_files(source_dir: Path, target_dir: Path, files: List[str]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for file in files:
        shutil.copyfile(source_dir / file, target_dir / file)


# ---------------- the cook ----------------

def cook_map(export_dir: Path, map_name: str, mode_sublevels: Dict[str, List[str]], out_dir: Path,
             gltfpack_cmd: Path, cache_dir: Optional[Path] = None) -> dict:
    """Cook one map into ``out_dir``; returns its pins document (see the module docstring).

    ``mode_sublevels`` maps each game mode to the sublevel suffixes it loads visibly, its
    own first (``{"Spearhead": ["Spearhead", "Crusher"]}``); modes the map has no sublevel
    for are skipped.
    """
    started = time.time()
    scene = Scene(export_dir, map_name)
    modes = {mode: map_levels(map_name, suffixes, scene.levels) for mode, suffixes in mode_sublevels.items()}
    modes = {mode: levels for mode, levels in modes.items() if levels and levels[0].lower() == f"{map_name}_{mode}".lower()}
    settings = {
        "cook_version": COOK_VERSION, "gltfpack": GLTFPACK_VERSION, "pack_options": PACK_OPTIONS,
        "foliage_pack_options": FOLIAGE_PACK_OPTIONS, "margin": MARGIN, "landscape_stride": LANDSCAPE_STRIDE,
        "modes": modes,
    }
    digest = input_hash(scene, settings)

    cached = _cached(cache_dir, map_name, digest)
    if cached is not None:
        _copy_files(cache_dir / map_name, out_dir, cooked_files(cached))
        logger.info(f"Map {map_name}: unchanged, copied from the cook cache ({time.time() - started:.1f}s)")
        return cached

    baked = baking.bake(scene, LANDSCAPE_STRIDE)
    for warning in baked["warnings"]:
        logger.warning(f"Map {map_name}: bake: {warning}")
    box = playable_box(baked)
    if box is None:
        logger.warning(f"Map {map_name}: no navigation mesh, so no playable box: nothing is cut away")
    drawn = drawn_mask(baked, box)
    always = baking.level_mask(baked)
    foliage = foliage_mask(baked)

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {"base": f"{map_name}.glb", "foliage": f"{map_name}.foliage.glb"}
    mode_files = {}
    with tempfile.TemporaryDirectory(prefix=f"cook-{map_name}-") as work:
        work_dir = Path(work)
        base = _pack(baked, always & drawn & ~foliage, out_dir / files["base"], gltfpack_cmd, work_dir)
        if base is None:
            raise ValueError(f"Map {map_name}: nothing to draw")
        logger.info(f"Map {map_name}: base: {_describe(base)}")

        foliage_counts = _pack(baked, always & drawn & foliage, out_dir / files["foliage"], gltfpack_cmd, work_dir,
                               FOLIAGE_PACK_OPTIONS)
        if foliage_counts is None:
            files["foliage"] = None
        else:
            logger.info(f"Map {map_name}: foliage: {_describe(foliage_counts)}")

        for mode, levels in modes.items():
            file = f"{map_name}.{mode}.glb"
            counts = _pack(baked, sublevel_mask(baked, levels) & drawn, out_dir / file, gltfpack_cmd, work_dir)
            mode_files[mode] = file if counts else None
            if counts:
                logger.info(f"Map {map_name}: {mode} geometry ({', '.join(levels)}): {_describe(counts)}")

    objectives = extract(scene)
    pins = {
        "version": COOK_VERSION,
        "input_hash": digest,
        "map": map_name,
        "units": UNITS,
        "playable_box": [[round(float(value), 1) for value in corner] for corner in box] if box is not None else None,
        "files": files,
        "modes": {
            mode: {"sublevels": levels, "file": mode_files[mode], "pins": mode_pins(objectives, levels)}
            for mode, levels in modes.items()
        },
    }
    (out_dir / pins_file_name(map_name)).write_text(json.dumps(pins, separators=(",", ":")), encoding="utf-8")
    summary = ", ".join(f"{mode} {len(entry['pins'])}" for mode, entry in pins["modes"].items()) or "no game modes"
    logger.info(f"Map {map_name}: pins: {summary} ({time.time() - started:.1f}s)")

    if cache_dir is not None:
        shutil.rmtree(cache_dir / map_name, ignore_errors=True)
        _copy_files(out_dir, cache_dir / map_name, cooked_files(pins))
    return pins


def _describe(counts: dict) -> str:
    return (f"{counts['instances']} instances of {counts['unique_meshes']} meshes, "
            f"{counts['triangles']:,} triangles ({counts['unique_triangles']:,} unique) -> "
            f"{counts['packed_triangles']:,} ({counts['packed_unique_triangles']:,} unique), "
            f"{counts['bytes'] / 1e6:.1f} MB")
