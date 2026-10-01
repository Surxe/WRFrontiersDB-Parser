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

WEAPON_REF = "OBJID_CharacterModule::BP_Weapon_TeslaFeed.0"


class TestAbilityWeaponHoist(unittest.TestCase):
    """WeaponInfos under misc.spawn_actor_action.ActorClass moves to weapon_char_module_ref."""

    def _parse(self, misc):
        ability = ability_parser.Ability.__new__(ability_parser.Ability)
        ability.id = "BP_Module_Test_Torso.1"
        ability.source_data = {}
        with mock.patch.object(ability_parser.Ability, "_parse_from_data", return_value={"misc": misc}):
            ability._parse()
        return ability

    def test_emptied_containers_are_dropped(self):
        ability = self._parse({
            "EffectType": "Support",
            "spawn_actor_action": {"ActorClass": {"WeaponInfos": WEAPON_REF}},
        })
        self.assertEqual(ability.weapon_char_module_ref, WEAPON_REF)
        self.assertEqual(ability.misc, {"EffectType": "Support"})

    def test_remaining_data_is_kept(self):
        ability = self._parse({
            "spawn_actor_action": {
                "ActorClass": {"WeaponInfos": WEAPON_REF, "LifeTime": 10.0},
                "FlyTime": 1.0,
            },
        })
        self.assertEqual(ability.weapon_char_module_ref, WEAPON_REF)
        self.assertEqual(ability.misc, {
            "spawn_actor_action": {"ActorClass": {"LifeTime": 10.0}, "FlyTime": 1.0},
        })


if __name__ == '__main__':
    unittest.main()
