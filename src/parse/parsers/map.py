# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""Maps: the game's map list, plus the 3D maps cooked from the map export.

The map list is the game's own: the maps the matchmaking queues list
(``DA_QueueCommonData.MapsLocalization``, keyed by the map's folder), the maps
ST_MapNames names that no queue lists (the tutorial), and the firing range,
which has no name. Each is cooked from MAPS_EXPORT_DIR (``maps/cook.py``) into
``Maps/`` in the output; ``Objects/Map.json`` lists them with their game modes and
file names (relative to the output root, as the Site loads them).

A game mode's map content is the sublevels its Blueprint loads visibly
(``BP_GameMode_*`` ``SubLevels``: ``_Spearhead`` and ``_Crusher``, not the hidden
``_PostCombat``); the first is the mode's own and names it.
"""

import glob
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from utils import OPTIONS, get_json_data, join_path
from parsers.object import ParseObject
from parsers.localization_table import parse_localization
from parsers.game_mode import GameMode
from maps.cook import cook_map, pins_file_name
from maps.gltfpack import GLTFPACK_DIR, ensure_gltfpack

QUEUE_COMMON_DATA_FILE = r"WRFrontiers\Content\Sparrow\UI\Meta\QueueModes\DataAssets\DA_QueueCommonData.json"
MAP_NAMES_FILE = r"WRFrontiers\Content\Sparrow\Localization\ST_MapNames.json"
MAP_NAMES_TABLE_ID = "/Game/Sparrow/Localization/ST_MapNames.ST_MapNames"
MAP_NAME_KEY_PREFIX = "Map_"
GAME_MODES_DIR = r"WRFrontiers\Content\Sparrow\GameModes"
# Played, but named nowhere.
UNNAMED_MAPS = ["FiringRange"]
# Onboarding modes replay a regular mode's sublevels against bots; the regular one names them.
SKIPPED_GAME_MODE_BPS = ("Onboarding",)
# The queue screen names game modes by code (GameModesLocalization); the game links a code to
# its Blueprint server side, so the link is kept here, keyed by the mode's own sublevel suffix.
MODE_CODES = {
    "BeaconRush": "BCN",
    "Spearhead": "SPH",
    "TeamDeathMatch": "TDM",
    "TeamDeathMatchPlus": "TDMPlus",
    "Elimination": "ELM",
    "EliminationPlus": "ELMPlus",
    "CTF": "CTF",
}
# Where the cooked files go, in the output and so in the data repo.
MAPS_OUTPUT_DIR = "Maps"
# Cooks of unchanged maps are copied from here instead of cooked again (see maps/cook.py).
MAP_COOK_CACHE_DIR = GLTFPACK_DIR.parent / "map_cook_cache"


class Map(ParseObject):
    objects = dict()

    def _parse(self):
        localization = self.source_data.get("localization")
        if localization:
            self.name = parse_localization(localization)
        self.queued = self.source_data["queued"]


def _properties(file_path: str, type_name: str) -> dict:
    entries = get_json_data(file_path)
    entry = next((entry for entry in entries if entry.get("Type") == type_name), None)
    if entry is None:
        raise ValueError(f"No {type_name} in {file_path}")
    return entry.get("Properties", entry)


def map_entries(export_dir: str) -> Dict[str, dict]:
    """``{map folder: {"localization": ..., "queued": bool}}`` for every released map, queued
    ones first in the game's order. Raises if the queue asset lists no maps."""
    queue = _properties(join_path(export_dir, QUEUE_COMMON_DATA_FILE), "SQueueModesCommonDataAsset")
    maps = {item["Key"]: {"localization": item["Value"], "queued": True}
            for item in queue.get("MapsLocalization") or [] if item.get("Key")}
    if not maps:
        raise ValueError(f"No maps in MapsLocalization of {QUEUE_COMMON_DATA_FILE}")

    names_file = join_path(export_dir, MAP_NAMES_FILE)
    if os.path.exists(names_file):
        table = next(entry for entry in get_json_data(names_file) if entry.get("Type") == "StringTable")
        for key in table["StringTable"]["KeysToEntries"]:
            folder = key[len(MAP_NAME_KEY_PREFIX):] if key.startswith(MAP_NAME_KEY_PREFIX) else None
            if folder and folder not in maps:
                maps[folder] = {"localization": {"TableId": MAP_NAMES_TABLE_ID, "Key": key}, "queued": False}
    for folder in UNNAMED_MAPS:
        maps.setdefault(folder, {"localization": None, "queued": False})
    return maps


def game_mode_sublevels(export_dir: str) -> Dict[str, List[str]]:
    """``{mode: [sublevel suffix, ...]}``: the sublevels each game mode Blueprint loads
    visibly, its own first (``{"Spearhead": ["Spearhead", "Crusher"]}``)."""
    modes = {}
    pattern = os.path.join(join_path(export_dir, GAME_MODES_DIR), "**", "BP_GameMode_*.json")
    for bp_file in sorted(glob.glob(pattern, recursive=True)):
        if any(skipped in os.path.basename(bp_file) for skipped in SKIPPED_GAME_MODE_BPS):
            continue
        sublevels = next((entry["Properties"]["SubLevels"] for entry in get_json_data(bp_file)
                          if "SubLevels" in entry.get("Properties", {})), None)
        if not sublevels:
            continue
        suffixes = [sublevel["Suffix"].lstrip("_") for sublevel in sublevels if sublevel.get("bVisible", True)]
        mode = sublevels[0]["Suffix"].lstrip("_")
        if not suffixes or suffixes[0] != mode:
            logger.warning(f"Game mode Blueprint {os.path.basename(bp_file)} does not load its own sublevel _{mode} visibly; skipped")
            continue
        if mode in modes:
            logger.warning(f"Game mode {mode} is loaded by more than one Blueprint; keeping the first, skipping {os.path.basename(bp_file)}")
            continue
        modes[mode] = suffixes
    return modes


def _resolved(localization: Optional[dict]) -> bool:
    """A parse_localization result that found English text (unknown keys come back as the key)."""
    return bool(localization) and bool(localization.get("en")) and localization.get("en") != localization.get("Key")


def _game_mode_asset(export_dir: str, mode: str) -> Optional[str]:
    pattern = os.path.join(join_path(export_dir, GAME_MODES_DIR), "**", f"DA_GameMode_{mode}.json")
    files = glob.glob(pattern, recursive=True)
    return files[0] if files else None


def mode_info(export_dir: str, mode: str, queue_modes: Dict[str, dict]) -> dict:
    """A mode's name (the queue screen's, else its DA_GameMode's) and GameMode ref."""
    info = {"id": mode}
    code = MODE_CODES.get(mode)
    if code is None:
        logger.warning(f"Game mode {mode} has no queue code in MODE_CODES; add it so the mode gets the queue screen's name")
    name = parse_localization(queue_modes[code]) if code in queue_modes else None
    game_mode_file = _game_mode_asset(export_dir, mode)
    if not _resolved(name) and game_mode_file:
        display_name = _properties(game_mode_file, "SGameModeDataAsset").get("DisplayName")
        if isinstance(display_name, dict):
            name = parse_localization(display_name)
    if name:
        info["name"] = name
    else:
        logger.warning(f"Game mode {mode} has no name")
    game_mode_id = f"DA_GameMode_{mode}.0"
    if GameMode.get_from_id(game_mode_id) is not None:
        info["game_mode_ref"] = GameMode.id_to_ref(game_mode_id)
    return info


def parse_maps(to_file=False):
    """Cook every released map from MAPS_EXPORT_DIR and list them as Map objects."""
    export_dir = str(OPTIONS.export_dir)
    maps_export_dir = Path(OPTIONS.maps_export_dir)
    out_dir = Path(OPTIONS.output_dir) / MAPS_OUTPUT_DIR

    entries = map_entries(export_dir)
    mode_sublevels = game_mode_sublevels(export_dir)
    queue = _properties(join_path(export_dir, QUEUE_COMMON_DATA_FILE), "SQueueModesCommonDataAsset")
    queue_modes = {item["Key"]: item["Value"] for item in queue.get("GameModesLocalization") or []}
    # The queue screen's order, then any mode it does not list.
    order = [mode for code in queue_modes for mode, mode_code in MODE_CODES.items() if mode_code == code]
    mode_sublevels = {mode: mode_sublevels[mode] for mode in order + sorted(mode_sublevels) if mode in mode_sublevels}
    logger.info(f"Maps: {', '.join(entries)}; game modes: "
                + "; ".join(f"{mode} ({', '.join(suffixes)})" for mode, suffixes in mode_sublevels.items()))

    gltfpack_cmd = ensure_gltfpack()
    modes_by_id = {}
    for map_id, entry in entries.items():
        if not (maps_export_dir / "maps" / map_id / "scene.json").is_file():
            logger.error(f"Map {map_id} is in the game's map list but not in the map export {maps_export_dir}; not cooked")
            continue
        logger.debug(f"Parsing {Map.__name__} {map_id}")
        game_map = Map(map_id, entry)
        pins = cook_map(maps_export_dir, map_id, mode_sublevels, out_dir, gltfpack_cmd, MAP_COOK_CACHE_DIR)

        game_map.files = {
            "base": f"{MAPS_OUTPUT_DIR}/{pins['files']['base']}",
            "pins": f"{MAPS_OUTPUT_DIR}/{pins_file_name(map_id)}",
        }
        if pins["files"]["foliage"]:
            game_map.files["foliage"] = f"{MAPS_OUTPUT_DIR}/{pins['files']['foliage']}"
        game_map.modes = []
        for mode, cooked in pins["modes"].items():
            if mode not in modes_by_id:
                modes_by_id[mode] = mode_info(export_dir, mode, queue_modes)
            mode_entry = dict(modes_by_id[mode])
            if cooked["file"]:
                mode_entry["file"] = f"{MAPS_OUTPUT_DIR}/{cooked['file']}"
            game_map.modes.append(mode_entry)

    total = sum(file.stat().st_size for file in out_dir.glob("*")) if out_dir.is_dir() else 0
    logger.info(f"Maps: cooked {len(Map.objects)} maps, {total / 1e6:.1f} MB in {out_dir}")

    if to_file:
        Map.to_file()
