import os
import sys
import types
import unittest
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

from parsers import ability as ability_parser  # noqa: E402

DEFAULT = "/Game/Sparrow/Abilities/BP_Ability_DashDefault"
CHASSIS = "/Game/Sparrow/Modules/Armor/Loki/BP_Module_Loki_Chassis"


def ref(path):
    return {"ObjectName": "irrelevant", "ObjectPath": path}


# Shaped like the 2026-11-05 export: BP_Ability_DashDefault's actions (the archetypes) and
# Loki's chassis Blueprint, whose actions store only the fields they change.
EXPORT = {
    f"{DEFAULT}.3": {"Type": "SDashAction", "Properties": {
        "CanStartOnGround": True, "CanStartMidair": True, "bHasDuration": True, "Duration": 1.5,
        "MaxSpeedModifier": ref(f"{DEFAULT}.16"), "bPlayVisualFX": True}},
    f"{DEFAULT}.4": {"Type": "SDashAction", "Properties": {
        "CanStartOnGround": True, "Duration": 0.4, "StartImpulse": {"X": 0.0, "Y": 0.0, "Z": 500.0},
        "VelocityThreshold": 0.75}},
    f"{DEFAULT}.5": {"Type": "SDashAction", "Properties": {
        "CanStartOnGround": True, "StartDelay": 0.5, "bHasDuration": True, "Duration": 0.35,
        "VerticalAcceleration": 1000.0}},
    f"{DEFAULT}.16": {"Type": "SSimpleFloatChannelModifier", "Properties": {
        "Value": 2500.0, "Type": "ESFloatChannelModifierType::Add"}},
    # Loki action 0: turns off the air start, shortens it, has its own modifier
    f"{CHASSIS}.16": {"Type": "SDashAction", "Template": ref(f"{DEFAULT}.3"), "Properties": {
        "CanStartMidair": False, "Duration": 1.0, "MaxSpeedModifier": ref(f"{CHASSIS}.42"), "bPlayVisualFX": True}},
    f"{CHASSIS}.42": {"Type": "SSimpleFloatChannelModifier", "Properties": {
        "Value": 3000.0, "Type": "ESFloatChannelModifierType::Add"}},
    # Loki action 1: only a bigger hop
    f"{CHASSIS}.17": {"Type": "SDashAction", "Template": ref(f"{DEFAULT}.4"), "Properties": {
        "StartImpulse": {"X": 0.0, "Y": 0.0, "Z": 700.0}}},
    # Loki action 2: shorter, stronger, with a speed cap; keeps the 0.5 s start delay
    f"{CHASSIS}.18": {"Type": "SDashAction", "Template": ref(f"{DEFAULT}.5"), "Properties": {
        "Duration": 0.3, "VerticalAcceleration": 1400.0, "bHasVelocityThreshold": True, "VelocityThreshold": 4500.0}},
    # An action identical to its archetype: no Properties of its own
    f"{CHASSIS}.19": {"Type": "SDashAction", "Template": ref(f"{DEFAULT}.5")},
    # Loki action 7: its own, no archetype
    f"{CHASSIS}.23": {"Type": "SDashAction", "Properties": {
        "CanStartOnGround": True, "CanStartMidair": True, "bHasDuration": True, "Duration": 1.0,
        "bBlocksAirControl": True, "bPlayVisualFX": True}},
}


class TestDashActionArchetypes(unittest.TestCase):
    """Each chassis dash action is merged over BP_Ability_DashDefault's action it was made from."""

    def _parse(self, paths):
        ability = ability_parser.Ability.__new__(ability_parser.Ability)
        ability.id = "BP_Module_Loki_Chassis.1"
        with mock.patch.object(ability_parser, "asset_to_data", side_effect=lambda asset: EXPORT[asset["ObjectPath"]]):
            return ability._p_actions([ref(path) for path in paths])

    def test_own_fields_override_the_archetype(self):
        action_0, action_1, action_2 = self._parse([f"{CHASSIS}.16", f"{CHASSIS}.17", f"{CHASSIS}.18"])
        self.assertEqual(action_0, {
            "CanStartOnGround": True, "CanStartMidair": False, "bHasDuration": True, "Duration": 1.0,
            "MaxSpeedModifier": {"Value": 3000.0, "Type": "Add"},
        })
        self.assertEqual(action_1, {
            "CanStartOnGround": True, "Duration": 0.4, "StartImpulse": {"X": 0.0, "Y": 0.0, "Z": 700.0},
            "VelocityThreshold": 0.75,
        })
        # the published data lost this start delay before the merge
        self.assertEqual(action_2, {
            "CanStartOnGround": True, "StartDelay": 0.5, "bHasDuration": True, "Duration": 0.3,
            "VerticalAcceleration": 1400.0, "bHasVelocityThreshold": True, "VelocityThreshold": 4500.0,
        })

    def test_action_without_own_properties_keeps_its_index(self):
        actions = self._parse([f"{CHASSIS}.19", f"{CHASSIS}.23"])
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0], {
            "CanStartOnGround": True, "StartDelay": 0.5, "bHasDuration": True, "Duration": 0.35,
            "VerticalAcceleration": 1000.0,
        })

    def test_action_without_archetype_is_its_own_fields(self):
        (action_7,) = self._parse([f"{CHASSIS}.23"])
        self.assertEqual(action_7, {
            "CanStartOnGround": True, "CanStartMidair": True, "bHasDuration": True, "Duration": 1.0,
            "bBlocksAirControl": True,
        })

    def test_modifier_without_own_properties_comes_from_its_archetype(self):
        modifier = {"Type": "SSimpleFloatChannelModifier", "Template": ref(f"{DEFAULT}.16")}
        ability = ability_parser.Ability.__new__(ability_parser.Ability)
        ability.id = "BP_Module_Loki_Chassis.1"
        lookup = dict(EXPORT, modifier=modifier)
        with mock.patch.object(ability_parser, "asset_to_data", side_effect=lambda asset: lookup[asset["ObjectPath"]]):
            self.assertEqual(ability._p_max_speed_modifier(ref("modifier")), {"Value": 2500.0, "Type": "Add"})


if __name__ == '__main__':
    unittest.main()
