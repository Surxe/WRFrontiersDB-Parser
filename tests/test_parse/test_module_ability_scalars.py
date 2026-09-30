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

from parsers import module as module_parser  # noqa: E402


class TestModuleAbilityScalars(unittest.TestCase):
    """abilities_scalars[i] must stay aligned with the character module's abilities_refs[i]."""

    def _parse(self, parsed_scalars):
        module = module_parser.Module.__new__(module_parser.Module)
        module.id = "DA_Module_ChassisTest.2"
        elems = [{"ObjectPath": f"elem{i}"} for i in range(len(parsed_scalars))]
        with mock.patch.object(module_parser, "asset_to_data", side_effect=lambda elem: elem), \
                mock.patch.object(module_parser.Module, "_p_scalars", side_effect=parsed_scalars):
            module._p_ability_scalars(elems)
        return module.abilities_scalars

    def test_empty_scaler_keeps_its_index(self):
        # e.g. a chassis whose first ability scaler only holds bAllowStatsReporting
        charge_regen = {"default_scalars": {"ChargeRegenDuration": 20.0}}
        self.assertEqual(self._parse([{}, charge_regen]), [{}, charge_regen])

    def test_scaler_without_properties_keeps_its_index(self):
        # _p_scalars returns None for a struct without 'Properties'
        charge_regen = {"default_scalars": {"ChargeRegenDuration": 20.0}}
        self.assertEqual(self._parse([None, charge_regen]), [{}, charge_regen])


if __name__ == '__main__':
    unittest.main()
