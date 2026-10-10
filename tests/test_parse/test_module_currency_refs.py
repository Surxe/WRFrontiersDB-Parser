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
from parsers import object as object_parser  # noqa: E402
from parsers.currency import Currency, currency_name_to_ref  # noqa: E402


class TestModuleCurrencyRefs(unittest.TestCase):
    """Module levels name their currency by bare asset name; the ref built from it must
    point at a Currency that exists, under the same id an ObjectPath reference gives it."""

    def setUp(self):
        patches = [
            mock.patch.dict(Currency.objects, clear=True),
            # Keep the export off disk: any currency asset path resolves to an empty asset
            mock.patch.object(object_parser, 'asset_path_to_file_path_and_index', return_value=("currency.json", 0)),
            mock.patch.object(object_parser, 'get_json_data', return_value={"Properties": {}}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_ref_points_at_a_parsed_currency(self):
        ref = currency_name_to_ref("DA_Meta_Currency_Alloys")
        self.assertEqual(ref, "OBJID_Currency::DA_Meta_Currency_Alloys.0")
        self.assertIn(Currency.ref_to_id(ref), Currency.objects)

    def test_ref_matches_an_object_path_reference(self):
        by_path = Currency.create_from_asset(
            {"ObjectPath": "/Game/Sparrow/Mechanics/Meta/Entities/Currency/DA_Meta_Currency_Intel.0"})
        self.assertEqual(currency_name_to_ref("DA_Meta_Currency_Intel"), by_path.to_ref())
        self.assertEqual(len(Currency.objects), 1)

    def test_analysis_constants_are_the_refs_modules_emit(self):
        # Analysis and enrich_rarity_upgrade_costs look costs up by these with .get(); a
        # mismatch reads as zero cost rather than failing
        self.assertEqual(analysis.ALLOY_CURRENCY_REF, currency_name_to_ref("DA_Meta_Currency_Alloys"))
        self.assertEqual(analysis.INTEL_CURRENCY_REF, currency_name_to_ref("DA_Meta_Currency_Intel"))


if __name__ == '__main__':
    unittest.main()
