# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from parsers.object import ParseObject
from parsers.module_stats_table import ModuleStatsTable
from utils import OPTIONS, join_path, get_json_data

GAME_INSTANCE_PATH = r"WRFrontiers\Content\Sparrow\Core\BP_GameInstance.json"
GAME_INSTANCE_CDO_NAME = "Default__BP_GameInstance_C"

# Role -> the module scalar (and ModuleStatsTable key) holding the armor of a zone in
# that role, on the module whose meshes link it. The game binds these in native code,
# so this is the one hand-kept mapping; a role missing here is logged as an error.
STAT_KEY_BY_ROLE = {
    "Torso": "Armor",
    "LeftShoulder": "Armor",
    "RightShoulder": "Armor",
    "Pelvis": "PelvisArmor",
    "LeftLeg": "LegsArmor",
    "RightLeg": "LegsArmor",
}


class ArmorZone(ParseObject):
    """A robot health pool (SArmorZone). Module meshes link to one via their
    SArmorZoneLink (CharacterModule meshes' `armor_zone`); several meshes linking
    the same zone share its armor (a spider chassis's two left legs).

    `role` is the slot the game assigns the zone in BP_GameInstance's
    RobotArmorZones (Torso, LeftShoulder, Pelvis, LeftLeg, ...). `stat_key` is the
    linking module's scalar holding the zone's armor (module_scalars levels), and
    `module_stat_ref` that stat's ModuleStat (name, units).
    """
    objects = dict()  # Dictionary to hold all ArmorZone instances

    def _parse(self):
        props = self.source_data.get("Properties", {})

        key_to_parser_function = {
            "TypeOfPilotReaction": None,  # voice line
        }

        self._process_key_to_parser_function(key_to_parser_function, props)


def parse_armor_zones():
    """Create every robot armor zone with its role, from BP_GameInstance's
    RobotArmorZones. Run after parse_modules(), so zones that module meshes link
    but RobotArmorZones does not name are reported.
    """
    game_instance_path = join_path(OPTIONS.export_dir, GAME_INSTANCE_PATH)
    elements = get_json_data(game_instance_path)
    cdo = next((element for element in elements if element.get("Name") == GAME_INSTANCE_CDO_NAME), None)
    robot_armor_zones = (cdo or {}).get("Properties", {}).get("RobotArmorZones")
    if not robot_armor_zones:
        logger.error(f"No RobotArmorZones in {GAME_INSTANCE_CDO_NAME} ({game_instance_path}); armor zones have no roles")
        return

    # Each key is a role slot holding its zone (PelvisArmorZone -> DA_ArmorZone_Pelvis),
    # so a slot a patch adds gets its role with no parser change.
    for slot, zone_asset in robot_armor_zones.items():
        role = slot.removesuffix("ArmorZone")
        zone = ArmorZone.create_from_asset(zone_asset)
        if getattr(zone, "role", None) is not None:
            logger.error(f"ArmorZone {zone.id} has two roles: {zone.role} and {role}")
            continue
        zone.role = role
        _set_stat(zone)

    for zone in ArmorZone.objects.values():
        if getattr(zone, "role", None) is None:
            logger.error(f"ArmorZone {zone.id} is linked by a module but has no role in RobotArmorZones")


def _set_stat(zone):
    """The zone's armor stat, from its role; its ModuleStat via the stats tables."""
    stat_key = STAT_KEY_BY_ROLE.get(zone.role)
    if stat_key is None:
        logger.error(f"ArmorZone {zone.id} has role {zone.role} with no armor stat in STAT_KEY_BY_ROLE")
        return
    zone.stat_key = stat_key
    stat_refs = {table.stats_refs.get(stat_key) for table in ModuleStatsTable.objects.values()}
    if len(stat_refs) != 1 or None in stat_refs:
        logger.error(f"ArmorZone {zone.id}: stat {stat_key} resolves to {stat_refs} across the ModuleStatsTables")
        return
    zone.module_stat_ref = stat_refs.pop()
