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

import analysis  # noqa: E402


class TestMountsAreMirrored(unittest.TestCase):
    """A module with several mounts is fine for ability descriptions only if every mount carries the same abilities."""

    def _mirrored(self, abilities_by_character_module):
        # abilities_by_character_module: {character_module_ref: [ability name key, ...]}
        character_modules = {
            ref: types.SimpleNamespace(abilities_refs=[f"{ref}:{i}" for i in range(len(keys))])
            for ref, keys in abilities_by_character_module.items()
        }
        abilities = {
            f"{ref}:{i}": types.SimpleNamespace(name={"Key": key, "TableNamespace": "Ability_name"})
            for ref, keys in abilities_by_character_module.items() for i, key in enumerate(keys)
        }
        mounts = [{"character_module_ref": ref} for ref in abilities_by_character_module]
        with mock.patch.object(analysis.CharacterModule, "get_from_ref", side_effect=character_modules.get), \
                mock.patch.object(analysis.Ability, "get_from_ref", side_effect=abilities.get):
            return analysis.mounts_are_mirrored(mounts)

    def test_left_right_copies_of_one_ability(self):
        # Cerberus Mk. II shoulder: Left and Right each hold their own copy of Gatekeeper Frame
        self.assertTrue(self._mirrored({
            "BP_Module_Cerberus_ShoulderL_02.0": ["ABL_name_GatekeeperFrame"],
            "BP_Module_Cerberus_ShoulderR_02.0": ["ABL_name_GatekeeperFrame"],
        }))

    def test_different_abilities_per_mount(self):
        self.assertFalse(self._mirrored({
            "BP_Module_TestL.0": ["ABL_name_A"],
            "BP_Module_TestR.0": ["ABL_name_B"],
        }))

    def test_different_ability_counts_per_mount(self):
        self.assertFalse(self._mirrored({
            "BP_Module_TestL.0": ["ABL_name_A"],
            "BP_Module_TestR.0": ["ABL_name_A", "ABL_name_B"],
        }))


if __name__ == '__main__':
    unittest.main()
