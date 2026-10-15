"""Loader for an exported map scene (``scene.json`` + ``actors.jsonl``).

A scene describes one root world: its levels (the persistent level, its
streaming sublevels and, nested, the level instances placed in them) and every
actor in those levels with its components and resolved world transforms.

Coordinates are Unreal's: centimeters, left-handed, +Z up, +X forward. A
transform is ``{"t": [x, y, z], "q": [x, y, z, w], "s": [x, y, z]}`` and maps a
local point to ``t + rotate(q, s * point)``.
"""
import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import numpy as np

# Level kinds that are part of the map no matter which game mode is played.
ALWAYS_KINDS = ("persistent", "streaming_always_loaded")
DYNAMIC_KIND = "streaming_dynamic"
INSTANCE_KIND = "level_instance"


def quat_matrix(q) -> np.ndarray:
    """3x3 rotation matrix of quaternion [x, y, z, w], for column vectors."""
    x, y, z, w = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def trs_matrix(t, q, s) -> np.ndarray:
    """4x4 matrix M such that ``world = M @ [x, y, z, 1]``."""
    matrix = np.eye(4)
    matrix[:3, :3] = quat_matrix(q) * np.asarray(s, dtype=float)[None, :]
    matrix[:3, 3] = t
    return matrix


def transform_matrix(transform: dict) -> np.ndarray:
    return trs_matrix(transform["t"], transform["q"], transform["s"])


def instance_matrix(instance) -> np.ndarray:
    """4x4 matrix of one instanced-mesh entry [tx,ty,tz, qx,qy,qz,qw, sx,sy,sz]."""
    return trs_matrix(instance[0:3], instance[3:7], instance[7:10])


def apply(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Transform (N, 3) points by a 4x4 matrix."""
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def forward(transform: dict) -> np.ndarray:
    """Unit +X (facing) direction of a transform in world space."""
    return quat_matrix(transform["q"])[:, 0]


class Scene:
    """One exported map. ``export_dir`` is the export root, the parent of ``maps/``."""

    def __init__(self, export_dir, map_name: str) -> None:
        self.export_dir = Path(export_dir)
        self.map_name = map_name
        self.map_dir = self.export_dir / "maps" / map_name
        with open(self.map_dir / "scene.json", encoding="utf-8") as scene_file:
            self.data = json.load(scene_file)
        self.levels: List[dict] = self.data["levels"]
        self.templates: Dict[str, dict] = self.data["templates"]
        self.meshes: Dict[str, dict] = self.data["meshes"]
        self.response_sets: List[dict] = self.data.get("collision_response_sets", [])

    def actors(self) -> Iterator[dict]:
        """Every actor, in id order. Streamed: the file is large, filter as you go."""
        with open(self.map_dir / self.data.get("actors_file", "actors.jsonl"), encoding="utf-8") as actors_file:
            for line in actors_file:
                if line.strip():
                    yield json.loads(line)

    def file(self, relative_file: str) -> Path:
        """Absolute path of a file the scene refers to (paths are relative to the export root)."""
        return self.export_dir / relative_file

    def navmesh_bounds(self, actors: Optional[Iterable[dict]] = None) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Min and max corner of the navigation mesh, i.e. of where a robot can stand;
        None for a map without one. Pass the navmesh actors when they are already at hand."""
        points = []
        for actor in (self.actors() if actors is None else actors):
            if "navmesh" not in actor:
                continue
            with open(self.file(actor["navmesh"]["file"]), encoding="utf-8") as navmesh_file:
                for tile in json.load(navmesh_file)["tiles"]:
                    points.append(np.asarray(tile["vertices"], dtype=float).reshape(-1, 3))
        if not points:
            return None
        stacked = np.concatenate(points)
        return stacked.min(axis=0), stacked.max(axis=0)

    def level_chain(self, level_index: int) -> List[dict]:
        """The level and its ancestors, innermost first."""
        chain = []
        current: Optional[int] = level_index
        while current is not None:
            level = self.levels[current]
            chain.append(level)
            current = level.get("parent")
        return chain

    def streaming_root(self, level_index: int) -> dict:
        """The streaming sublevel (or persistent level) a level ultimately belongs to:
        itself, or for a level instance the level its chain of instances is placed in."""
        level = self.levels[level_index]
        while level["kind"] == INSTANCE_KIND:
            level = self.levels[level["parent"]]
        return level

    def level_names(self, kind: str) -> List[str]:
        return [level["name"] for level in self.levels if level["kind"] == kind and not level.get("missing")]

    def active_levels(self, dynamic_levels=()) -> np.ndarray:
        """Boolean mask over level indices: loaded when only the always-loaded
        sublevels plus the named dynamic ones (e.g. ``["Mont_Spearhead"]``) are in."""
        wanted = set(dynamic_levels)
        mask = np.zeros(len(self.levels), dtype=bool)
        for level in self.levels:
            if level.get("missing"):
                continue
            root = self.streaming_root(level["index"])
            mask[level["index"]] = root["kind"] in ALWAYS_KINDS or root["name"] in wanted
        return mask

    def effective_props(self, obj: dict) -> dict:
        """An actor's or component's properties with its template defaults filled in.

        Cooked levels only store what differs from the class or Blueprint
        defaults; this merges the object's own ``props`` over its template.
        Keys the export resolves into fields of their own (transforms, mesh,
        shape, collision) are absent from ``props`` and may be stale here.
        """
        merged = json.loads(json.dumps(self.templates.get(obj.get("template") or "", {})))
        _merge(merged, obj.get("props") or {})
        return merged


def _merge(target: dict, source: dict) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value


def object_name(reference) -> Optional[str]:
    """Name of the object a serialized reference points at, e.g.
    ``{"ObjectName": "BP_X_C'Lvl:PersistentLevel.BP_X_C_1'"}`` -> ``BP_X_C_1``."""
    if not isinstance(reference, dict) or "ObjectName" not in reference:
        return None
    quoted = reference["ObjectName"].split("'")
    path = quoted[1] if len(quoted) > 1 else quoted[0]
    return path.rsplit(".", 1)[-1].rsplit(":", 1)[-1]
