"""World physics of a map: gravity, terminal velocity and kill height.

The engine resolves them like this (UE 5.4):

- gravity: the persistent level's world settings ``GlobalGravityZ`` when its
  ``bGlobalGravitySet`` is on, else the project's ``PhysicsSettings.DefaultGravityZ``;
- terminal velocity: a physics volume's ``TerminalVelocity``, which defaults to
  ``PhysicsSettings.DefaultTerminalVelocity`` (the world's default physics volume always does);
- kill height: the world settings ``KillZ``; a map that doesn't set it keeps the engine's
  "never" default, so it is left out.

``PhysicsSettings`` comes from the game's ``.ini`` files, which the map export copies into
``config/``. They are layered the way the engine reads them for the Windows client: the
engine's base files, then the project's ``DefaultEngine.ini``, then its Windows file. Later
files win.
"""
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

from loguru import logger

PHYSICS_SETTINGS_SECTION = "/Script/Engine.PhysicsSettings"
# Engine config layers, lowest priority first (paths under the map export's config/).
ENGINE_INI_LAYERS = (
    "Engine/Config/Base.ini",
    "Engine/Config/BaseEngine.ini",
    "Engine/Config/Windows/BaseWindowsEngine.ini",
    "Engine/Config/Windows/WindowsEngine.ini",
    "WRFrontiers/Config/DefaultEngine.ini",
    "WRFrontiers/Config/Windows/WindowsEngine.ini",
)
PHYSICS_KEYS = ("DefaultGravityZ", "DefaultTerminalVelocity")


def ini_section_values(config_dir: Path, layers: Iterable[str], section: str) -> Dict[str, str]:
    """Plain ``Key=Value`` lines of one ``.ini`` section across layered files, later files winning.

    Array operators (``+Key``, ``-Key``, ``.Key``, ``!Key``) are not resolved; the scalar
    settings read here never use them. Missing files are skipped.
    """
    values: Dict[str, str] = {}
    for layer in layers:
        path = Path(config_dir) / layer
        if not path.is_file():
            continue
        in_section = False
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                in_section = line[1:-1] == section
                continue
            if in_section and "=" in line and line[0] not in "+-.!":
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def physics_settings(maps_export_dir: Path) -> Dict[str, float]:
    """``{DefaultGravityZ, DefaultTerminalVelocity}`` from the game's config.

    A missing key is logged as an error and left out (the engine's BaseEngine.ini always sets
    both, so it means the config export is incomplete); the maps then publish without it.
    """
    values = ini_section_values(Path(maps_export_dir) / "config", ENGINE_INI_LAYERS, PHYSICS_SETTINGS_SECTION)
    missing = [key for key in PHYSICS_KEYS if key not in values]
    if missing:
        logger.error(f"[{PHYSICS_SETTINGS_SECTION}] {', '.join(missing)} not found in the map export's config "
                     f"({Path(maps_export_dir) / 'config'}); maps are published without it")
    return {key: float(values[key]) for key in PHYSICS_KEYS if key in values}


def world_settings(map_dir: Path) -> Optional[dict]:
    """The persistent level's world settings actor properties (``props``), or None if the scene has none."""
    map_dir = Path(map_dir)
    scene = json.loads((map_dir / "scene.json").read_text(encoding="utf-8"))
    persistent = next((level for level in scene.get("levels") or [] if level.get("kind") == "persistent"), None)
    actor_id = persistent.get("world_settings_actor") if persistent else None
    if actor_id is None:
        return None
    with open(map_dir / scene.get("actors_file", "actors.jsonl"), encoding="utf-8") as actors_file:
        for line in actors_file:
            actor = json.loads(line)
            if actor.get("id") == actor_id:
                return actor.get("props") or {}
    return None


def map_physics(settings: Optional[dict], physics: Dict[str, float]) -> dict:
    """A map's resolved ``{GravityZ, TerminalVelocity, KillZ?}`` (cm, cm/s), as the engine resolves them.

    ``GlobalGravityZ`` absent with ``bGlobalGravitySet`` on is its C++ default, 0.
    """
    settings = settings or {}
    resolved = {}
    if settings.get("bGlobalGravitySet"):
        resolved["GravityZ"] = float(settings.get("GlobalGravityZ", 0.0))
    elif "DefaultGravityZ" in physics:
        resolved["GravityZ"] = physics["DefaultGravityZ"]
    if "DefaultTerminalVelocity" in physics:
        resolved["TerminalVelocity"] = physics["DefaultTerminalVelocity"]
    if "KillZ" in settings:
        resolved["KillZ"] = float(settings["KillZ"])
    return resolved


def parse_map_physics(maps_export_dir: Path, map_id: str, physics: Dict[str, float]) -> dict:
    """``map_physics`` for one map of the map export; logs an error when it has no world settings."""
    settings = world_settings(Path(maps_export_dir) / "maps" / map_id)
    if settings is None:
        logger.error(f"Map {map_id} has no world settings actor in its persistent level; its gravity falls back to "
                     f"PhysicsSettings, which is only right if the map sets no override")
    return map_physics(settings, physics)
