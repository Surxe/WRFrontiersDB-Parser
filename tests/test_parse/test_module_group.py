import copy
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

from parsers import module_group as module_group_parser  # noqa: E402
from parsers.localization import Localization  # noqa: E402
from parsers.module_group import MODULE_GROUPS_DATA, ModuleGroup  # noqa: E402
from parsers.module_type import ModuleType  # noqa: E402


class TestModuleGroupNames(unittest.TestCase):
    def setUp(self):
        # generate_all writes the localized en back into MODULE_GROUPS_DATA
        patches = [
            mock.patch.object(module_group_parser, 'MODULE_GROUPS_DATA', copy.deepcopy(MODULE_GROUPS_DATA)),
            mock.patch.dict(ModuleGroup.objects, clear=True),
            mock.patch.dict(ModuleType.objects, clear=True),
            mock.patch.dict(Localization.objects, clear=True),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_every_name_is_a_game_key_or_keyless(self):
        """A group name either points at the game's localization or carries no key at all;
        a key the game does not have cannot be resolved by anything that reads the data."""
        for group_id, data in MODULE_GROUPS_DATA.items():
            name = data['name']
            with self.subTest(group_id=group_id):
                if 'Key' in name:
                    self.assertEqual(name['TableNamespace'], 'Component_Tags')
                else:
                    self.assertNotIn('TableNamespace', name)
                    self.assertTrue(name['InvariantString'])
                    self.assertEqual(name['en'], name['InvariantString'])

    def test_keyed_name_gets_en_from_localization(self):
        Localization('en', {'Component_Tags': {'CMP_Type_Titan_Torso': 'Titan Torso'}})

        ModuleGroup.generate_all()

        self.assertEqual(
            ModuleGroup.objects['titan-torsos'].name,
            {'Key': 'CMP_Type_Titan_Torso', 'TableNamespace': 'Component_Tags', 'en': 'Titan Torso'},
        )

    def test_keyless_name_is_not_looked_up(self):
        en_loc = Localization('en', {'Component_Tags': {}})

        with mock.patch.object(en_loc, 'localize_from_name', wraps=en_loc.localize_from_name) as localize:
            ModuleGroup.generate_all()

        self.assertEqual(
            ModuleGroup.objects['titan-shoulder'].name,
            {'InvariantString': 'Titan Shoulder', 'en': 'Titan Shoulder'},
        )
        for call in localize.call_args_list:
            self.assertIn('Key', call.args[0])


if __name__ == '__main__':
    unittest.main()
