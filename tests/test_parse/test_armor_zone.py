import os
import sys
import types
import unittest
from contextlib import ExitStack
from unittest import mock

os.environ['SHOULD_PARSE'] = 'false'
os.environ.setdefault('EXPORT_DIR', '/tmp/test_export')
os.environ.setdefault('OUTPUT_DIR', '/tmp/test_output')

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
parse_path = os.path.join(src_path, 'parse')
# Parsers import both 'parsers.*' and 'parse.parsers.*'. As in run.py, 'parse' must be
# the src/parse package, not src/parse/parse.py (which wins once src/parse is on sys.path)
if not hasattr(sys.modules.get('parse'), '__path__'):
    parse_pkg = types.ModuleType('parse')
    parse_pkg.__path__ = [parse_path]
    sys.modules['parse'] = parse_pkg
sys.path.insert(0, src_path)
sys.path.insert(0, parse_path)

from parsers import armor_zone as armor_zone_parser  # noqa: E402
from parsers.armor_zone import ArmorZone, parse_armor_zones  # noqa: E402
from parsers.module_stats_table import ModuleStatsTable  # noqa: E402


def _zone_ref(name):
    return {
        "ObjectName": f"SArmorZone'{name}'",
        "ObjectPath": f"/Game/Sparrow/ArmorZones/{name}.0",
    }


ZONE_ASSET = [{"Type": "SArmorZone", "Properties": {"TypeOfPilotReaction": "ESVoiceoverReactionArmorType::ChassisZoneChanged"}}]


def _export(stack, game_instance=None):
    """Serve BP_GameInstance and SArmorZone assets without an export dir."""
    def get_json_data(file_path, index=None):
        if file_path.endswith("BP_GameInstance.json"):
            return game_instance
        return ZONE_ASSET[index] if index is not None else ZONE_ASSET

    stack.enter_context(mock.patch.object(armor_zone_parser, "OPTIONS", types.SimpleNamespace(export_dir="/export")))
    stack.enter_context(mock.patch.object(armor_zone_parser, "get_json_data", side_effect=get_json_data))
    stack.enter_context(mock.patch("parsers.object.get_json_data", side_effect=get_json_data))
    stack.enter_context(mock.patch("parsers.object.asset_path_to_file_path_and_index",
                                   side_effect=lambda path: (path, int(path.rsplit(".", 1)[-1]))))


class TestParseArmorZones(unittest.TestCase):
    """Roles come from BP_GameInstance's RobotArmorZones, keyed by zone object."""

    def setUp(self):
        ArmorZone.objects.clear()
        table = ModuleStatsTable.__new__(ModuleStatsTable)
        table.id = "DA_ModuleStatsTable.0"
        table.stats_refs = {
            "Armor": "OBJID_ModuleStat::DA_ModuleStat_Armor.0",
            "PelvisArmor": "OBJID_ModuleStat::DA_ModuleStat_PelvisArmor.0",
            "LegsArmor": "OBJID_ModuleStat::DA_ModuleStat_LegsArmor.0",
        }
        self._tables = mock.patch.dict(ModuleStatsTable.objects, {table.id: table}, clear=True)
        self._tables.start()

    def tearDown(self):
        ArmorZone.objects.clear()
        self._tables.stop()

    def _parse(self, robot_armor_zones):
        game_instance = [
            {"Type": "BlueprintGeneratedClass", "Name": "BP_GameInstance_C"},
            {"Type": "BP_GameInstance_C", "Name": "Default__BP_GameInstance_C",
             "Properties": {"RobotArmorZones": robot_armor_zones}},
        ]

        with ExitStack() as stack:
            _export(stack, game_instance)
            parse_armor_zones()

    def test_roles_from_robot_armor_zones(self):
        self._parse({
            "PelvisArmorZone": _zone_ref("DA_ArmorZone_Pelvis"),
            "LeftLegArmorZone": _zone_ref("DA_ArmorZone_LeftLeg"),
        })
        self.assertEqual(ArmorZone.get_from_id("DA_ArmorZone_Pelvis.0").role, "Pelvis")
        self.assertEqual(ArmorZone.get_from_id("DA_ArmorZone_LeftLeg.0").role, "LeftLeg")
        self.assertEqual(ArmorZone.get_from_id("DA_ArmorZone_LeftLeg.0").to_dict(), {
            "id": "DA_ArmorZone_LeftLeg.0",
            "role": "LeftLeg",
            "stat_key": "LegsArmor",
            "module_stat_ref": "OBJID_ModuleStat::DA_ModuleStat_LegsArmor.0",
        })

    def test_new_role_gets_role_but_no_stat(self):
        # a slot a patch adds: its role comes through, its missing stat mapping is an error
        with mock.patch.object(armor_zone_parser.logger, "error") as error:
            self._parse({"TailArmorZone": _zone_ref("DA_ArmorZone_Tail")})
        zone = ArmorZone.get_from_id("DA_ArmorZone_Tail.0")
        self.assertEqual(zone.role, "Tail")
        self.assertFalse(hasattr(zone, "stat_key"))
        self.assertIn("STAT_KEY_BY_ROLE", error.call_args.args[0])

    def test_linked_zone_without_role_is_an_error(self):
        # a zone a module mesh links (created before parse_armor_zones) that RobotArmorZones does not name
        with ExitStack() as stack:
            _export(stack)
            ArmorZone.create_from_asset(_zone_ref("DA_ArmorZone_Tail"))
        with mock.patch.object(armor_zone_parser.logger, "error") as error:
            self._parse({"TorsoArmorZone": _zone_ref("DA_ArmorZone_Torso")})
        self.assertIsNone(getattr(ArmorZone.get_from_id("DA_ArmorZone_Tail.0"), "role", None))
        self.assertIn("DA_ArmorZone_Tail.0", error.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
