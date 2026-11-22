"""What a robot collides with on a map, as ``Maps/<Map>.collision.bin``.

A robot's movement capsule sweeps against the components whose collision blocks it
(``collision_profiles.CollisionProfiles.blocks_robot``), and of those only against the geometry a
simple query hits:

- ``DefaultShapeComplexity`` is ``CTF_UseSimpleAsComplex`` in the game's config, so a mesh at the
  default trace flag collides by its simple shapes (boxes, spheres, capsules, convex hulls). A mesh
  with none is not hit at all: its triangle mesh only carries the complex-query flag
  (``FBodyInstance`` filter data, ``CollisionQueryFilterCallback``).
- A ``CTF_UseComplexAsSimple`` body collides by its cooked triangle mesh.
- Brushes collide by their convex hulls, shape components by their box, sphere or capsule, and
  the landscape by its cooked collision heightfields (and mesh collision pieces), holes included.

Each component's collision is its native class default, then its template chain, then, with
``bUseDefaultCollision``, its mesh's default body (see ``resolve``). The native defaults of the
classes the maps use are listed below with where they come from.

Shapes are scaled the way UE scales them (``FKBoxElem::GetFinalScaled`` and its siblings,
``Engine/Private/PhysicsEngine/BodySetup.cpp``; ``ChaosInterfaceUtils.cpp`` ``CreateGeometry``):

- box: extents times ``|scale|`` along the box's own axes (no shear), centre times the scale;
- sphere: radius times the smallest ``|scale|``;
- capsule: radius times ``max(|sx|, |sy|)``, length from ``|sz|``, clamped as UE clamps them;
- convex hull and triangle mesh: the full scale, applied to the vertices.

The file is a GLB-style container (magic ``WRFC``): a JSON chunk describing the parts and arrays,
then a binary chunk holding them. Units and axes are Unreal's. See ``FORMAT`` for the layout.
"""
import json
import re
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
from loguru import logger

from .bake import _is_map_boundary, enclosing_volume_flags, FLAG_MAP_BOUNDARY, FLAG_MAP_CEILING
from .collision_profiles import CUSTOM, CollisionProfiles, enabled_name
from .scene import ALWAYS_KINDS, DYNAMIC_KIND, Scene, quat_matrix

FORMAT_VERSION = 1
MAGIC = b"WRFC"
_JSON_CHUNK = 0x4E4F534A
_BINARY_CHUNK = 0x004E4942

# Bits of a collider's flags.
FLAG_HIDDEN = 1  # nothing drawn there (hidden actor or component, brush, shape component)
FLAG_BOUNDARY = 2  # the wall that fences in the playable area
FLAG_CEILING = 4  # the slab that caps the playable area
FLAG_DESTRUCTIBLE = 8  # can be destroyed in a match; exported intact
FLAG_MOVING = 16  # moves in a match (SMovingPlatform); exported where it starts
# Triangle meshes only: the body setup's bDoubleSidedGeometry. Without it Chaos culls the back faces
# of a complex-as-simple mesh in sweeps unless the swept shape starts overlapping them
# (ChaosInterfaceUtils.cpp SetCullsBackFaceRaycast(!bDoubleSided); FTriangleMeshSweepVisitor::VisitSweep).
FLAG_DOUBLE_SIDED = 32
FLAG_NAMES = {"hidden": FLAG_HIDDEN, "boundary": FLAG_BOUNDARY, "ceiling": FLAG_CEILING,
              "destructible": FLAG_DESTRUCTIBLE, "moving": FLAG_MOVING, "double_sided": FLAG_DOUBLE_SIDED}

SIMPLE_AS_COMPLEX = "CTF_UseSimpleAsComplex"
COMPLEX_AS_SIMPLE = "CTF_UseComplexAsSimple"
# [/Script/PhysicsCore.PhysicsSettingsCore] DefaultShapeComplexity in the game's DefaultEngine.ini.
DEFAULT_TRACE_FLAG = SIMPLE_AS_COMPLEX
_SMALL = 1e-4  # UE_KINDA_SMALL_NUMBER, the floor Chaos puts under every extent

# Native class defaults: the profile each component class's constructor sets (UE 5.4.4 source,
# and for WRF's own class its constructor in the 2026-11-05 exe).
COMPONENT_DEFAULTS = {
    "UPrimitiveComponent": "BlockAll",  # PrimitiveComponent.cpp
    "UBrushComponent": "BlockAll",  # inherits UPrimitiveComponent's
    "UStaticMeshComponent": "BlockAllDynamic",  # StaticMeshComponent.cpp
    "UInstancedStaticMeshComponent": "BlockAllDynamic",
    "UHierarchicalInstancedStaticMeshComponent": "BlockAllDynamic",
    "UFoliageInstancedStaticMeshComponent": "BlockAllDynamic",
    "USplineMeshComponent": "NoCollision",  # SplineMeshComponent.cpp
    "UBoxComponent": "OverlapAllDynamic",  # UShapeComponent's constructor
    "USphereComponent": "OverlapAllDynamic",
    "UCapsuleComponent": "OverlapAllDynamic",
    "UDrawSphereComponent": "OverlapAllDynamic",
    "CookedLandscapeCollisionComponent": "BlockAll",  # LandscapeCollision.cpp
    "CookedLandscapeMeshCollisionComponent": "BlockAll",
}
# By component class name, ahead of the CUE4Parse type: WRF component classes.
COMPONENT_CLASS_DEFAULTS = {
    "SSpawnComponent": "NoCollision",  # constructor 0x14530e7f0
    "BP_SpawnComponent_C": "NoCollision",
}
# Default subobjects an actor constructor sets differently, by (actor class, component name):
# (profile, collision enabled set after it or None, bUseDefaultCollision). The export gives these
# components no template (their archetype is a native default object), so they are matched by name.
# WRF's are from its constructors in the 2026-11-05 exe (SetCollisionProfileName is vtable +0x738,
# SetCollisionEnabled +0x730); see the planning notes, 10-collision.md section 1.2.
ACTOR_DEFAULTS: Dict[Tuple[str, str], Tuple[str, Optional[str], bool]] = {
    ("StaticMeshActor", "StaticMeshComponent0"): ("BlockAll", None, True),  # StaticMeshActor.cpp
    ("BlockingVolume", "BrushComponent0"): ("InvisibleWall", None, False),  # BlockingVolume.cpp
    ("TriggerVolume", "BrushComponent0"): ("Trigger", None, False),
    ("PhysicsVolume", "BrushComponent0"): ("OverlapAllDynamic", None, False),  # and KillZVolume
    ("PostProcessVolume", "BrushComponent0"): ("NoCollision", None, False),
    ("NavMeshBoundsVolume", "BrushComponent0"): ("NoCollision", None, False),
    ("LightmassImportanceVolume", "BrushComponent0"): ("NoCollision", None, False),
    ("CullDistanceVolume", "BrushComponent0"): ("NoCollision", None, False),
    ("AudioVolume", "BrushComponent0"): ("NoCollision", None, False),
    ("NavModifierVolume", "BrushComponent0"): ("OverlapAll", None, False),
    ("Volume", "BrushComponent0"): ("OverlapAll", None, False),  # Volume.cpp
    ("Brush", "BrushComponent0"): ("BlockAll", None, False),
    ("NavigationObjectBase", "CollisionCapsule"): ("NoCollision", None, False),  # player starts
    ("SBeaconActor", "MeshComponent"): ("NoCollision", None, False),  # 0x1458b4070
    ("SBeaconActor", "ContestZoneComponent"): ("OverlapOnlyPawn", None, False),
    ("SBeaconActor", "CaptureZoneComponent"): ("OverlapOnlyPawn", None, False),
    ("SBeaconActor", "SpawnComponent"): ("NoCollision", None, False),  # an SSpawnComponent
    ("STeamPlayerStart", "SpawnComponent"): ("NoCollision", None, False),  # an SSpawnComponent
    ("SBlockablePlayerStart", "MeshComponent"): ("NoCollision", None, False),  # 0x1458dc140
    ("SCTFUploadZone", "UploadZone"): ("OverlapOnlyPawn", None, False),  # 0x145912de0
    ("SCTFUploadZone", "ZoneMesh"): ("NoCollision", None, False),
    ("SCTFUploadZone", "TeamCylinderMesh"): ("NoCollision", None, False),
    ("SDamagingVolume", "CollisionComponent"): ("OverlapOnlyPawn", None, False),  # 0x1455b5dc0
    ("SDrillActor", "Button"): ("PhysicsActor", None, False),  # 0x145452f90
    ("SDrillActor", "Platform"): ("BlockAll", None, False),
    ("SDrillActor", "DamageZoneIndicator"): ("NoCollision", None, False),
    ("SDrillActor", "DamageZone"): ("OverlapOnlyPawn", None, False),
    ("SDrillActor", "Drill"): ("BlockAllDynamic", "NoCollision", False),
    ("SDummySpawner", "CapsuleComponent"): ("NoCollision", None, False),  # 0x1455b6190
    ("SMovingPlatform", "MeshComponent"): ("BlockAll", None, False),  # 0x1455f9810
    ("SQuantumCore", "InteractionZone"): ("OverlapOnlyPawn", None, False),  # 0x145913320
    ("SQuantumCore", "CoreMesh"): ("NoCollision", None, False),
    ("SQuantumCore", "LightPillarMesh"): ("NoCollision", None, False),
    ("SWarpProbe", "MeshComponent"): ("NoCollision", None, False),  # 0x1458dca30
    ("SWarpProbe", "WarpDevice"): ("BlockAll", "NoCollision", False),
    ("SWarpProbe", "CaptureZoneComponent"): ("OverlapOnlyPawn", None, False),
    ("SWaterFXVolume", "BrushComponent0"): ("OverlapOnlyPawn", None, False),  # 0x1454146d0
}
# A template "<...>Default__<Class>:<Name>" is a default subobject inherited from a native constructor.
_NATIVE_SUBOBJECT_TEMPLATE = re.compile(r"Default__[^:/]+:[^.:/]+$")
_GEOMETRY_KINDS = ("static_mesh", "instanced_static_mesh", "spline_mesh", "brush", "box", "sphere", "capsule",
                   "landscape_collision")

FORMAT = {
    "units": "centimeters, Unreal axes (left-handed, +Z up)",
    "transform": "t = [x, y, z], q = [x, y, z, w], s = [x, y, z]; world = t + rotate(q, s * local)",
    "winding": "UE's own triangle order (as the render meshes): outward normal = (v2 - v0) x (v1 - v0)",
    "arrays": "{offset, count, type, width}: count rows of width values of type, little-endian, at offset in the binary chunk",
    "meta": "per collider [part, flags, object_type, source]: part index, FLAG bits, collision channel index, sources index",
    "boxes": "data: centre (3), rotation (4), half extents (3), world space",
    "spheres": "data: centre (3), radius",
    "capsules": "data: centre (3), rotation (4), radius, half length of the cylinder along local Z",
    "hulls": ("convex hull library, body space: vertices (3), triangles (3, vertex indices local to the hull; uint16 or "
              "uint32), ranges [first vertex, vertex count, first triangle, triangle count]. Hull triangles may be empty: "
              "build the hull from its points"),
    "hull_instances": "hull index and transform (10: t, q, s) per placed hull",
    "meshes": "triangle mesh library: same layout as hulls",
    "mesh_instances": "mesh index and transform per placed mesh",
    "heightfields": ("grid [rows, cols, first height, first hole cell or -1]; decode [min_value, height_per_unit]; "
                     "transform (t, q, s). Vertex (x, y) has height h = heights[first + y * cols + x]; "
                     "local point (x, y, min_value + h * height_per_unit), then the transform. Cells split along "
                     "(x, y) to (x + 1, y + 1); a hole cell (holes value 1, (rows - 1) * (cols - 1) per grid) has no collision"),
}


def trace_flag(body: dict) -> str:
    flag = (body.get("trace_flag") or "").split("::")[-1]
    return flag if flag and flag != "CTF_UseDefault" else DEFAULT_TRACE_FLAG


def simple_shape_count(body: dict) -> int:
    return sum(len(body.get(key) or []) for key in ("boxes", "spheres", "capsules", "convex"))


def queried_geometry(body: Optional[dict]) -> Optional[str]:
    """What a simple query hits on a body: ``"simple"``, ``"trimesh"``, or None for nothing
    (``ChaosInterfaceUtils.cpp`` ``CreateGeometry`` with the filter flags of ``FBodyInstance``)."""
    if not body:
        return None
    if trace_flag(body) == COMPLEX_AS_SIMPLE and body.get("trimesh"):
        return "trimesh"
    return "simple" if simple_shape_count(body) else None


# ---------------- collision settings ----------------

def native_default(actor: dict, component: dict, unknown: Optional[Counter] = None) -> Tuple[str, Optional[str], bool]:
    """(profile, collision enabled set after it, bUseDefaultCollision) of a component whose
    template chain sets nothing."""
    for cls in actor.get("class_chain") or [actor.get("class")]:
        hit = ACTOR_DEFAULTS.get((cls, component["name"]))
        if hit:
            return hit
    if unknown is not None and _NATIVE_SUBOBJECT_TEMPLATE.search(component.get("template") or ""):
        native_actor = next((cls for cls in actor.get("class_chain") or [] if not cls.endswith("_C")), actor.get("class"))
        unknown[f"{native_actor}.{component['name']}"] += 1
    profile = COMPONENT_CLASS_DEFAULTS.get(component.get("class") or "") or COMPONENT_DEFAULTS.get(component.get("native") or "")
    if profile is None:
        if unknown is not None:
            unknown[f"component class {component.get('native')}"] += 1
        profile = "BlockAll"
    return profile, None, False


def _custom(profiles: CollisionProfiles, base: dict, enabled=None, object_type=None, responses=None) -> dict:
    return {
        "enabled": enabled_name(enabled) if enabled is not None else base["enabled"],
        "object_type": profiles.channel_index(object_type) if object_type is not None else base["object_type"],
        "responses": responses if responses is not None else list(base["responses"]),
    }


def body_instance_collision(profiles: CollisionProfiles, instance: dict) -> dict:
    """A mesh body's default collision (``UBodySetup::DefaultInstance``). Unset fields keep the
    ``FBodyInstance`` defaults: profile Custom, QueryAndPhysics, WorldStatic, default responses."""
    named = profiles.profile(instance.get("CollisionProfileName") or CUSTOM)
    if named is not None:
        return dict(named)
    array = (instance.get("CollisionResponses") or {}).get("ResponseArray") or []
    return {
        "enabled": enabled_name(instance.get("CollisionEnabled", "QueryAndPhysics")),
        "object_type": profiles.channel_index(instance.get("ObjectType", "ECC_WorldStatic")),
        "responses": profiles.responses(array),
    }


def resolve(profiles: CollisionProfiles, actor: dict, component: dict, response_sets: List[dict],
            mesh_info: Callable[[str], Optional[dict]], unknown: Optional[Counter] = None) -> dict:
    """A component's effective collision: ``{"enabled", "object_type", "responses"}``.

    1. the native default (``native_default``);
    2. what its template chain sets (the export's ``collision``);
    3. with ``bUseDefaultCollision`` on a static or instanced mesh, the mesh's default body instead
       (``UStaticMeshComponent::UpdateCollisionFromStaticMesh``);
    4. a named profile replaces all fields (``FBodyInstance::FixupData``); ``Custom`` keeps the set
       fields over the native default profile's.
    """
    settings = component.get("collision") or {}
    base_profile, base_enabled, base_use_default = native_default(actor, component, unknown)
    if settings.get("use_default", base_use_default) and component["kind"] in ("static_mesh", "instanced_static_mesh"):
        info = mesh_info(component.get("mesh") or "")
        collision = (info or {}).get("collision")
        if collision is not None:
            instance = collision.get("default_instance") or {}
            if not instance and collision.get("default_profile"):
                instance = {"CollisionProfileName": collision["default_profile"]}
            return body_instance_collision(profiles, instance)

    profile_name = settings.get("profile", base_profile if base_enabled is None else CUSTOM)
    named = profiles.profile(profile_name)
    if named is not None:
        return dict(named)
    base = profiles.profile(base_profile) or profiles.profile("BlockAll")
    responses = profiles.responses(response_sets[settings["responses"]]) if "responses" in settings else None
    return _custom(profiles, base, settings.get("enabled", base_enabled), settings.get("object_type"), responses)


# ---------------- shapes ----------------

def quat_multiply(a, b) -> np.ndarray:
    """Hamilton product a * b of [x, y, z, w] quaternions (apply b, then a)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def scaled_box(box: dict, scale) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A body box under a component scale (``FKBoxElem::GetFinalScaled``): (centre, rotation, half
    extents) in the body's frame. Extents scale along the box's own axes."""
    scale = np.asarray(scale, dtype=float)
    half = np.maximum(np.asarray(box["size"], dtype=float) * np.abs(scale) * 0.5, _SMALL)
    return np.asarray(box["center"], dtype=float) * scale, np.asarray(box.get("q", [0, 0, 0, 1]), dtype=float), half


def scaled_sphere(sphere: dict, scale) -> Tuple[np.ndarray, float]:
    """``FKSphereElem::GetFinalScaled``: radius times the smallest |scale|."""
    scale = np.asarray(scale, dtype=float)
    return np.asarray(sphere["center"], dtype=float) * scale, max(float(sphere["radius"]) * float(np.abs(scale).min()), _SMALL)


def scaled_capsule(capsule: dict, scale) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """``FKSphylElem::GetFinalScaled``: (centre, rotation, radius, half length of the cylinder)."""
    scale = np.asarray(scale, dtype=float)
    absolute = np.abs(scale)
    radius, length = float(capsule["radius"]), float(capsule["length"])
    half_total = max((length + radius * 2.0) * absolute[2] * 0.5, 0.1)
    scaled_radius = min(max(radius * max(absolute[0], absolute[1]), 0.1), half_total)
    cylinder = max(0.1, (half_total - scaled_radius) * 2.0)
    return (np.asarray(capsule["center"], dtype=float) * scale, np.asarray(capsule.get("q", [0, 0, 0, 1]), dtype=float),
            max(scaled_radius, _SMALL), max(cylinder * 0.5, _SMALL))


def shape_body(component: dict) -> Optional[dict]:
    """The one-element body of a shape component (``UBoxComponent::UpdateBodySetup`` and siblings)."""
    shape = component.get("shape") or {}
    if component["kind"] == "box":
        extent = [value if value >= _SMALL else 1.0 for value in shape.get("box_extent", [32, 32, 32])]
        return {"boxes": [{"center": [0, 0, 0], "q": [0, 0, 0, 1], "size": [value * 2 for value in extent]}]}
    if component["kind"] == "sphere":
        radius = shape.get("sphere_radius", 32.0)
        return {"spheres": [{"center": [0, 0, 0], "radius": radius if radius >= _SMALL else 0.1}]}
    if component["kind"] == "capsule":
        radius = shape.get("capsule_radius", 22.0)
        half_height = shape.get("capsule_half_height", 44.0)
        return {"capsules": [{"center": [0, 0, 0], "q": [0, 0, 0, 1], "radius": radius,
                              "length": 2 * max(half_height - radius, 0.0)}]}
    return None


def _flat(values, width: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array.reshape(-1, width)


# ---------------- the collision of a map ----------------

@dataclass
class _Library:
    """Hulls or triangle meshes, each once: concatenated vertices and triangles plus ranges."""
    vertices: List[np.ndarray] = field(default_factory=list)
    triangles: List[np.ndarray] = field(default_factory=list)
    index: Dict[object, int] = field(default_factory=dict)

    def add(self, key, vertices, triangles) -> int:
        if key is not None and key in self.index:
            return self.index[key]
        self.vertices.append(np.asarray(vertices, dtype=np.float32).reshape(-1, 3))
        self.triangles.append(np.asarray(triangles, dtype=np.uint32).reshape(-1, 3))
        number = len(self.vertices) - 1
        if key is not None:
            self.index[key] = number
        return number


@dataclass
class MapCollision:
    """The robot-blocking collision of one map, before it is written."""
    map_name: str
    parts: List[dict] = field(default_factory=list)
    modes: Dict[str, List[str]] = field(default_factory=dict)
    lighting: List[str] = field(default_factory=list)
    dropped_sublevels: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    source_index: Dict[str, int] = field(default_factory=dict)
    boxes: List[list] = field(default_factory=list)
    spheres: List[list] = field(default_factory=list)
    capsules: List[list] = field(default_factory=list)
    meta: Dict[str, List[list]] = field(default_factory=lambda: defaultdict(list))
    hulls: _Library = field(default_factory=_Library)
    hull_instances: List[list] = field(default_factory=list)
    meshes: _Library = field(default_factory=_Library)
    mesh_instances: List[list] = field(default_factory=list)
    heightfield_grids: List[list] = field(default_factory=list)
    heightfield_decode: List[list] = field(default_factory=list)
    heightfield_transforms: List[list] = field(default_factory=list)
    heights: List[np.ndarray] = field(default_factory=list)
    holes: List[np.ndarray] = field(default_factory=list)
    stats: Counter = field(default_factory=Counter)

    def source(self, name: str) -> int:
        if name not in self.source_index:
            self.source_index[name] = len(self.sources)
            self.sources.append(name)
        return self.source_index[name]

    def counts(self) -> dict:
        return {
            "boxes": len(self.boxes), "spheres": len(self.spheres), "capsules": len(self.capsules),
            "hulls": len(self.hulls.vertices), "hull_instances": len(self.hull_instances),
            "meshes": len(self.meshes.vertices), "mesh_instances": len(self.mesh_instances),
            "heightfields": len(self.heightfield_grids),
        }

    def collider_count(self) -> int:
        counts = self.counts()
        return sum(counts[key] for key in ("boxes", "spheres", "capsules", "hull_instances", "mesh_instances", "heightfields"))


class _Builder:
    def __init__(self, scene: Scene, profiles: CollisionProfiles, out: MapCollision) -> None:
        self.scene = scene
        self.profiles = profiles
        self.out = out
        self.infos: Dict[str, Optional[dict]] = {}
        self.unknown: Counter = Counter()
        self.blob: Optional[np.ndarray] = None
        blob_name = scene.data.get("collision_file")
        if blob_name:
            self.blob = np.fromfile(scene.map_dir / blob_name, dtype=np.uint8)

    def mesh_info(self, mesh_path: str) -> Optional[dict]:
        if mesh_path not in self.infos:
            summary = self.scene.meshes.get(mesh_path) or {}
            info = None
            if summary.get("info"):
                with open(self.scene.file(summary["info"]), encoding="utf-8") as info_file:
                    info = json.load(info_file)
            self.infos[mesh_path] = info
        return self.infos[mesh_path]

    def array(self, reference: dict) -> np.ndarray:
        if self.blob is None:
            raise ValueError(f"Map {self.scene.map_name}: landscape collision refers to a collision file the scene does not name")
        dtype = np.dtype({"uint8": "<u1", "uint16": "<u2", "int32": "<i4", "float32": "<f4"}[reference["type"]])
        start = int(reference["offset"])
        return np.frombuffer(self.blob[start:start + reference["count"] * dtype.itemsize].tobytes(), dtype=dtype)

    # -- placing a body --

    def add_body(self, body: dict, transforms: Iterable[Tuple[np.ndarray, np.ndarray, np.ndarray]], meta: list,
                 key: Optional[str]) -> None:
        """A body (``.meshinfo.json`` collision layout) at each world transform (t, q, s)."""
        geometry = queried_geometry(body)
        if geometry == "trimesh":
            trimesh = body["trimesh"]
            mesh = self.out.meshes.add(key and ("mesh", key), _flat(trimesh["vertices"], 3), _flat(trimesh["indices"], 3))
            if body.get("double_sided"):
                meta = [meta[0], meta[1] | FLAG_DOUBLE_SIDED, *meta[2:]]
            for t, q, s in transforms:
                self.out.mesh_instances.append([mesh, *t, *q, *s])
                self.out.meta["mesh_instances"].append(meta)
            return
        hull_numbers = []
        for number, hull in enumerate(body.get("convex") or []):
            vertices = _flat(hull["vertices"], 3)
            # The body setup's hull triangles wind the other way to UE's render order.
            triangles = _flat(hull.get("indices") or [], 3)[:, [1, 0, 2]] if hull.get("indices") else np.zeros((0, 3))
            hull_numbers.append(self.out.hulls.add(key and ("hull", key, number), vertices, triangles))
        for t, q, s in transforms:
            rotation = quat_matrix(q)
            for box in body.get("boxes") or []:
                center, box_q, half = scaled_box(box, s)
                self.out.boxes.append([*(t + rotation @ center), *quat_multiply(q, box_q), *half])
                self.out.meta["boxes"].append(meta)
            for sphere in body.get("spheres") or []:
                center, radius = scaled_sphere(sphere, s)
                self.out.spheres.append([*(t + rotation @ center), radius])
                self.out.meta["spheres"].append(meta)
            for capsule in body.get("capsules") or []:
                center, capsule_q, radius, half_length = scaled_capsule(capsule, s)
                self.out.capsules.append([*(t + rotation @ center), *quat_multiply(q, capsule_q), radius, half_length])
                self.out.meta["capsules"].append(meta)
            for hull in hull_numbers:
                self.out.hull_instances.append([hull, *t, *q, *s])
                self.out.meta["hull_instances"].append(meta)

    def add_landscape(self, component: dict, meta: list) -> None:
        collision = component["landscape_collision"]
        world = component["world"]
        t, q = np.asarray(world["t"], dtype=float), np.asarray(world["q"], dtype=float)
        s = np.asarray(world["s"], dtype=float)
        cell = float(collision["collision_scale"])
        if collision["type"] == "mesh":
            mesh = self.out.meshes.add(None, self.array(collision["vertices"]).reshape(-1, 3),
                                       self.array(collision["indices"]).reshape(-1, 3))
            self.out.mesh_instances.append([mesh, *t, *q, *(s * [cell, cell, 1.0])])
            # Landscape mesh collision is cooked with back-face culling off (ChaosCooking.cpp, default
            # bCullsBackFaceRaycast false; the landscape never sets it), so it blocks from both sides.
            self.out.meta["mesh_instances"].append([meta[0], meta[1] | FLAG_DOUBLE_SIDED, *meta[2:]])
            return
        heights = self.array(collision["heights"])
        rows, cols = int(collision["rows"]), int(collision["cols"])
        if len(heights) != rows * cols:
            raise ValueError(f"Map {self.scene.map_name}: landscape collision {component['name']} has {len(heights)} heights for {rows} x {cols}")
        first_hole = -1
        if collision.get("holes"):
            materials = self.array(collision["cell_materials"])
            first_hole = sum(len(hole) for hole in self.out.holes)
            self.out.holes.append((materials == 255).astype(np.uint8))
        self.out.heightfield_grids.append([rows, cols, sum(len(h) for h in self.out.heights), first_hole])
        self.out.heights.append(heights)
        self.out.heightfield_decode.append([collision["min_value"], collision["height_per_unit"]])
        self.out.heightfield_transforms.append([*t, *q, *(s * [cell, cell, 1.0 / 128.0])])
        self.out.meta["heightfields"].append(meta)


def _transform(world: dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.asarray(world["t"], dtype=float), np.asarray(world["q"], dtype=float), np.asarray(world["s"], dtype=float)


def _instance_transform(instance) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.asarray(instance[0:3], dtype=float), np.asarray(instance[3:7], dtype=float), np.asarray(instance[7:10], dtype=float)


def lighting_variants(scene: Scene) -> List[Tuple[str, float]]:
    """(sublevel suffix, weight) of the map's lighting variants (``SWorldSettings.LightingVariants``
    of the persistent level); one is loaded per match."""
    for actor in scene.actors():
        if actor["level"] != 0:
            continue
        variants = ((actor.get("props") or {}).get("LightingVariants") or {}).get("Variants")
        if variants:
            return [(variant["SubLevelSuffix"], float(variant.get("Weight", 1))) for variant in variants]
    return []


def build(scene: Scene, profiles: CollisionProfiles, modes: Dict[str, List[str]]) -> MapCollision:
    """The robot-blocking collision of a map. ``modes`` maps each game mode to the sublevels it
    loads (as ``cook.map_levels`` names them)."""
    out = MapCollision(map_name=scene.map_name, channels=list(profiles.channel_names))
    builder = _Builder(scene, profiles, out)
    by_lower = {level["name"].lower(): level["name"] for level in scene.levels if not level.get("missing")}

    # Parts: the base map, each sublevel a game mode loads, each lighting variant.
    out.parts.append({"id": "base", "kind": "base"})
    part_of_level: Dict[str, int] = {}
    for mode, levels in modes.items():
        out.modes[mode] = list(levels)
        for level in levels:
            if level.lower() not in part_of_level:
                part_of_level[level.lower()] = len(out.parts)
                out.parts.append({"id": level, "kind": "sublevel"})
    for suffix, weight in lighting_variants(scene):
        name = by_lower.get(f"{scene.map_name}{suffix}".lower())
        if name is None:
            logger.warning(f"Map {scene.map_name}: lighting variant {suffix} has no sublevel {scene.map_name}{suffix}")
            continue
        part_of_level[name.lower()] = len(out.parts)
        out.parts.append({"id": name, "kind": "lighting", "weight": weight})
        out.lighting.append(name)

    def part(level_index: int) -> Optional[int]:
        root = scene.streaming_root(level_index)
        if root["kind"] in ALWAYS_KINDS:
            return 0
        return part_of_level.get(root["name"].lower())

    out.dropped_sublevels = sorted(level["name"] for level in scene.levels
                                   if level["kind"] == DYNAMIC_KIND and not level.get("missing")
                                   and level["name"].lower() not in part_of_level)

    # Blocking volumes, to tell the wall and the ceiling from the other volumes afterwards.
    volumes: List[Tuple[str, int, np.ndarray, int]] = []  # (kind, index into its list, world box, hull count)
    response_sets = scene.response_sets
    for actor in scene.actors():
        actor_flags = FLAG_HIDDEN if actor.get("hidden") else 0
        chain = actor.get("class_chain") or [actor.get("class")]
        if "SDestructibleActor" in chain:
            actor_flags |= FLAG_DESTRUCTIBLE
        if "SMovingPlatform" in chain:
            actor_flags |= FLAG_MOVING
        for component in actor["components"]:
            kind = component["kind"]
            if kind not in _GEOMETRY_KINDS:
                continue
            part_index = part(actor["level"])
            if part_index is None:
                out.stats["dropped (sublevel not loaded)"] += 1
                continue
            collision = resolve(profiles, actor, component, response_sets, builder.mesh_info, builder.unknown)
            if not profiles.blocks_robot(collision):
                out.stats["not blocking"] += 1
                continue
            flags = actor_flags
            if component.get("visible") is False or component.get("hidden_in_game") or kind in ("brush", "box", "sphere", "capsule"):
                flags |= FLAG_HIDDEN
            if profiles.channel_names[collision["object_type"]] == "Destructible":
                flags |= FLAG_DESTRUCTIBLE
            if (profiles.channel_names[collision["object_type"]] == "MapBoundariesWall"
                    or (kind in ("static_mesh", "instanced_static_mesh", "spline_mesh") and _is_map_boundary(component))):
                flags |= FLAG_BOUNDARY
            mesh_path = component.get("mesh") or ""
            label = mesh_path.rsplit(".", 1)[-1] if mesh_path else component["name"]
            meta = [part_index, flags, collision["object_type"], out.source(f"{actor.get('class')}/{label}")]

            if kind == "landscape_collision":
                if component.get("landscape_collision"):
                    builder.add_landscape(component, meta)
                    out.stats["landscape collision components"] += 1
                continue
            if kind in ("static_mesh", "instanced_static_mesh"):
                info = builder.mesh_info(mesh_path) if mesh_path else None
                body = (info or {}).get("collision")
                if queried_geometry(body) is None:
                    out.stats["blocking, no queried geometry"] += 1
                    continue
                transforms = ([_transform(component["world"])] if kind == "static_mesh"
                              else [_instance_transform(instance) for instance in component.get("instances") or []])
                builder.add_body(body, transforms, meta, mesh_path)
            elif kind == "spline_mesh":
                body = component.get("body")
                if queried_geometry(body) is None:
                    out.stats["blocking, no queried geometry"] += 1
                    continue
                builder.add_body(body, [_transform(component["world"])], meta, None)
            elif kind == "brush":
                hulls = component.get("convex") or []
                if not hulls:
                    continue
                first = len(out.hull_instances)
                builder.add_body({"convex": hulls}, [_transform(component["world"])], meta, None)
                if "BlockingVolume" in chain:
                    corners = np.concatenate([_flat(hull["vertices"], 3) for hull in hulls])
                    t, q, s = _transform(component["world"])
                    world = (corners * s) @ quat_matrix(q).T + t
                    volumes.append(("hull_instances", first, np.stack([world.min(axis=0), world.max(axis=0)]), len(hulls)))
            else:
                builder.add_body(shape_body(component), [_transform(component["world"])], meta, None)
            out.stats[f"blocking {kind}"] += 1

    navmesh = scene.navmesh_bounds()
    if navmesh is not None and volumes:
        enclosing = enclosing_volume_flags(np.array([volume[2] for volume in volumes]),
                                           np.array([volume[3] for volume in volumes]), *navmesh)
        for (list_name, first, _, hull_count), bake_flags in zip(volumes, enclosing):
            extra = (FLAG_BOUNDARY if bake_flags & FLAG_MAP_BOUNDARY else 0) | (FLAG_CEILING if bake_flags & FLAG_MAP_CEILING else 0)
            for row in out.meta[list_name][first:first + hull_count]:
                row[1] |= extra

    for name, count in builder.unknown.most_common():
        logger.warning(f"Map {scene.map_name}: no known native collision default for {name} ({count} components); "
                       f"used its component class default. Add it to maps/collision.py ACTOR_DEFAULTS after checking the constructor")
    return out


# ---------------- the file ----------------

def _view(blob: bytearray, array: np.ndarray, type_name: str) -> dict:
    blob.extend(b"\0" * (-len(blob) % 8))
    offset = len(blob)
    data = np.ascontiguousarray(array)
    blob.extend(data.tobytes())
    width = int(data.shape[1]) if data.ndim > 1 else 1
    return {"offset": offset, "count": int(data.shape[0]) if data.ndim else 0, "type": type_name, "width": width}


def _rows(rows: List[list], width: int, dtype) -> np.ndarray:
    return np.asarray(rows, dtype=dtype).reshape(-1, width)


def _library(blob: bytearray, library: _Library) -> dict:
    vertices = np.concatenate(library.vertices) if library.vertices else np.zeros((0, 3), np.float32)
    triangles = np.concatenate(library.triangles) if library.triangles else np.zeros((0, 3), np.uint32)
    ranges, vertex, triangle = [], 0, 0
    for item_vertices, item_triangles in zip(library.vertices, library.triangles):
        ranges.append([vertex, len(item_vertices), triangle, len(item_triangles)])
        vertex += len(item_vertices)
        triangle += len(item_triangles)
    return {
        "vertices": _view(blob, vertices.astype("<f4"), "float32"),
        # Indices are local to their item: uint16 when every item has few enough vertices.
        "triangles": (_view(blob, triangles.astype("<u2"), "uint16") if all(len(v) <= 65536 for v in library.vertices)
                      else _view(blob, triangles.astype("<u4"), "uint32")),
        "ranges": _view(blob, _rows(ranges, 4, "<u4"), "uint32"),
    }


def _instances(blob: bytearray, rows: List[list], meta: List[list], index_name: str) -> dict:
    array = np.asarray(rows, dtype=float).reshape(-1, 11)
    return {
        index_name: _view(blob, array[:, 0].astype("<u4"), "uint32"),
        "transform": _view(blob, array[:, 1:].astype("<f4"), "float32"),
        "meta": _view(blob, _rows(meta, 4, "<u4"), "uint32"),
    }


def encode(collision: MapCollision) -> bytes:
    """The ``.collision.bin`` file: header, JSON chunk, binary chunk (see ``FORMAT``)."""
    blob = bytearray()
    meta = collision.meta
    heights = np.concatenate(collision.heights) if collision.heights else np.zeros(0, np.uint16)
    holes = np.concatenate(collision.holes) if collision.holes else np.zeros(0, np.uint8)
    document = {
        "format": "wrf-collision",
        "version": FORMAT_VERSION,
        "map": collision.map_name,
        "query": ("what a robot's movement capsule (collision profile Pawn) blocks on: simple shapes, "
                  "complex-as-simple triangle meshes and the landscape collision"),
        "layout": FORMAT,
        "flags": FLAG_NAMES,
        "channels": collision.channels,
        "parts": collision.parts,
        "modes": collision.modes,
        "lighting": collision.lighting,
        "dropped_sublevels": collision.dropped_sublevels,
        "sources": collision.sources,
        "counts": collision.counts(),
        "boxes": {"data": _view(blob, _rows(collision.boxes, 10, "<f4"), "float32"),
                  "meta": _view(blob, _rows(meta["boxes"], 4, "<u4"), "uint32")},
        "spheres": {"data": _view(blob, _rows(collision.spheres, 4, "<f4"), "float32"),
                    "meta": _view(blob, _rows(meta["spheres"], 4, "<u4"), "uint32")},
        "capsules": {"data": _view(blob, _rows(collision.capsules, 9, "<f4"), "float32"),
                     "meta": _view(blob, _rows(meta["capsules"], 4, "<u4"), "uint32")},
        "hulls": _library(blob, collision.hulls),
        "hull_instances": _instances(blob, collision.hull_instances, meta["hull_instances"], "hull"),
        "meshes": _library(blob, collision.meshes),
        "mesh_instances": _instances(blob, collision.mesh_instances, meta["mesh_instances"], "mesh"),
        "heightfields": {
            "grid": _view(blob, _rows(collision.heightfield_grids, 4, "<i4"), "int32"),
            "decode": _view(blob, _rows(collision.heightfield_decode, 2, "<f8"), "float64"),
            "transform": _view(blob, _rows(collision.heightfield_transforms, 10, "<f4"), "float32"),
            "meta": _view(blob, _rows(meta["heightfields"], 4, "<u4"), "uint32"),
            "heights": _view(blob, heights.astype("<u2"), "uint16"),
            "holes": _view(blob, holes.astype("<u1"), "uint8"),
        },
    }
    json_bytes = json.dumps(document, separators=(",", ":")).encode()
    json_bytes += b" " * (-len(json_bytes) % 8)
    blob.extend(b"\0" * (-len(blob) % 8))
    total = 12 + 8 + len(json_bytes) + 8 + len(blob)
    return b"".join([
        MAGIC + struct.pack("<II", FORMAT_VERSION, total),
        struct.pack("<II", len(json_bytes), _JSON_CHUNK), json_bytes,
        struct.pack("<II", len(blob), _BINARY_CHUNK), bytes(blob),
    ])


def decode(data: bytes) -> Tuple[dict, Callable[[dict], np.ndarray]]:
    """The JSON document of a ``.collision.bin`` and a function reading one of its array views."""
    if data[:4] != MAGIC:
        raise ValueError("not a WRFC collision file")
    version, total = struct.unpack_from("<II", data, 4)
    json_length, chunk = struct.unpack_from("<II", data, 12)
    if chunk != _JSON_CHUNK:
        raise ValueError("WRFC: no JSON chunk first")
    document = json.loads(data[20:20 + json_length])
    binary_start = 20 + json_length + 8
    dtypes = {"float32": "<f4", "float64": "<f8", "uint32": "<u4", "int32": "<i4", "uint16": "<u2", "uint8": "<u1"}

    def read(view: dict) -> np.ndarray:
        dtype = np.dtype(dtypes[view["type"]])
        start = binary_start + view["offset"]
        array = np.frombuffer(data[start:start + view["count"] * view["width"] * dtype.itemsize], dtype=dtype)
        return array.reshape(-1, view["width"]) if view["width"] > 1 else array

    return document, read
