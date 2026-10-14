"""Extract the gameplay objects of a map, per game mode.

Each game mode keeps its objects (spawn points, probes, beacons, power-up
spawners, ...) in a sublevel of its own that the game streams in on demand,
named ``<Map>_<Mode>``. Everything in those sublevels is reported; a small
table gives the well-known classes a stable ``type`` so a consumer does not
have to match Blueprint class names.
"""
import math
from typing import Dict, List, Optional

import numpy as np

from .scene import DYNAMIC_KIND, Scene, forward, object_name

# Matched in order against each name in the actor's class chain (Blueprint class
# first, then its native ancestors); the first hit wins.
TYPE_BY_CLASS = [
    ("WarpProbe", "warp_probe"),
    ("QuantumCore", "ctf_core"),
    ("CTFUploadZone", "ctf_upload_zone"),
    ("SBeaconActor", "beacon"),
    ("SDrillActor", "drill"),
    ("PowerUpSpawner", "powerup_spawner"),
    ("PlayerStart", "spawn"),
    ("SSpawner", "spawner"),
]

# Actors every level has that say nothing about the mode.
IGNORED_CLASSES = {"SWorldSettings", "WorldSettings", "Brush", "DefaultPhysicsVolume"}

# Properties that are editor/visual detail rather than gameplay data.
NOISE_PROPS = {"UberGraphFrame", "GoodSprite", "BadSprite", "FriendlyColor", "HostileColor", "NeutralColor"}


def classify(class_chain: List[str]) -> str:
    for name in class_chain:
        for needle, kind in TYPE_BY_CLASS:
            if needle in name:
                return kind
    return "other"


def _references(value) -> List[str]:
    """Names of the objects a property value points at, however deeply nested."""
    if isinstance(value, dict):
        name = object_name(value)
        if name is not None and set(value) <= {"ObjectName", "ObjectPath"}:
            return [name]
        return [name for nested in value.values() for name in _references(nested)]
    if isinstance(value, list):
        return [name for nested in value for name in _references(nested)]
    return []


def _zone(scene: Scene, component: dict) -> Optional[dict]:
    """World-space size of a component that marks a volume: a collision shape,
    or a mesh used as a trigger/indicator (capture zones are scaled cylinders)."""
    kind = component["kind"]
    if kind not in ("box", "sphere", "capsule", "static_mesh"):
        return None

    world = component["world"]
    scale = np.abs(np.asarray(world["s"], dtype=float))
    zone = {"component": component["name"], "class": component["class"], "kind": kind, "center": world["t"], "q": world["q"]}
    shape = component.get("shape") or {}
    if kind == "box":
        zone["half_extent"] = (np.asarray(shape["box_extent"]) * scale).tolist()
    elif kind == "sphere":
        zone["radius"] = float(shape["sphere_radius"] * scale.max())
    elif kind == "capsule":
        zone["radius"] = float(shape["capsule_radius"] * max(scale[0], scale[1]))
        zone["half_height"] = float(shape["capsule_half_height"] * scale[2])
    else:
        bounds = (scene.meshes.get(component.get("mesh") or "") or {}).get("bounds")
        if not bounds:
            return None
        zone["mesh"] = component["mesh"]
        # Local box of the mesh scaled into the world; the center offset is unrotated.
        zone["half_extent"] = (np.asarray(bounds["box_extent"]) * scale).tolist()
        zone["local_center"] = (np.asarray(bounds["origin"]) * np.asarray(world["s"], dtype=float)).tolist()
    if component.get("hidden_in_game") or component.get("visible") is False:
        zone["hidden"] = True
    return zone


def _is_reference(value) -> bool:
    """A lone object reference, or a list of nothing but those."""
    if isinstance(value, list):
        return bool(value) and all(_is_reference(item) for item in value)
    return isinstance(value, dict) and "ObjectName" in value and set(value) <= {"ObjectName", "ObjectPath"}


def _point(scene: Scene, actor: dict, level_actor_names: set) -> dict:
    effective = {key: value for key, value in scene.effective_props(actor).items() if key not in NOISE_PROPS}

    # References to other actors of the level (a probe's spawn points, a drill's
    # beacon) become links; references to assets (sounds, effects, classes) and to
    # the actor's own components carry no placement information and are dropped.
    links: Dict[str, List[str]] = {}
    props = {}
    for key, value in effective.items():
        names = [name for name in _references(value) if name in level_actor_names and name != actor["name"]]
        if names:
            links[key] = names
        if not _is_reference(value):
            props[key] = value

    world = actor["world"]
    direction = forward(world)
    point = {
        "actor": actor["id"],
        "name": actor["name"],
        "label": actor.get("label"),
        "class": actor["class"],
        "class_chain": actor["class_chain"],
        "type": classify(actor["class_chain"]),
        "position": world["t"],
        "forward": direction.tolist(),
        "yaw_degrees": math.degrees(math.atan2(direction[1], direction[0])),
        "zones": [zone for zone in (_zone(scene, component) for component in actor["components"]) if zone],
        "props": props,
        "links": links,
    }
    team = props.get("TeamId")
    if isinstance(team, dict) and "TeamId" in team:
        point["team"] = team["TeamId"]
    return point


def extract(scene: Scene) -> dict:
    """Gameplay objects of every dynamically loaded sublevel, keyed by sublevel name."""
    # References only make sense within one level, so actor names are grouped by it.
    actors_by_level: Dict[int, List[dict]] = {}
    for actor in scene.actors():
        if scene.streaming_root(actor["level"])["kind"] == DYNAMIC_KIND and actor["class"] not in IGNORED_CLASSES:
            actors_by_level.setdefault(actor["level"], []).append(actor)

    by_level: Dict[str, List[dict]] = {}
    for level_index, actors in actors_by_level.items():
        names = {actor["name"] for actor in actors}
        root_name = scene.streaming_root(level_index)["name"]
        by_level.setdefault(root_name, []).extend(_point(scene, actor, names) for actor in actors)

    prefix = f"{scene.map_name}_"
    modes = {}
    for level_name, points in by_level.items():
        # Sublevels with nothing recognizable are lighting, audio, camera or debug levels.
        if all(point["type"] == "other" for point in points):
            continue
        counts: Dict[str, int] = {}
        for point in points:
            counts[point["type"]] = counts.get(point["type"], 0) + 1
        mode = level_name[len(prefix):] if level_name.startswith(prefix) else level_name
        modes[mode] = {"level": level_name, "counts": counts, "points": points}

    settings = _world_settings(scene)
    return {
        "map": scene.map_name,
        "world": scene.data["world"],
        "display_name": ((settings.get("LocalizedName") or {}).get("SourceString")),
        "units": "centimeters, Unreal axes (left-handed, +Z up, yaw 0 faces +X)",
        "modes": modes,
    }


def _world_settings(scene: Scene) -> dict:
    """Effective properties of the root world's settings actor."""
    wanted = scene.levels[0].get("world_settings_actor")
    if wanted is None:
        return {}
    for actor in scene.actors():
        if actor["id"] == wanted:
            return scene.effective_props(actor)
        if actor["id"] > wanted:
            break
    return {}
