import json
import os
import shutil
import sys
import tempfile
import types
import unittest

os.environ['SHOULD_PARSE'] = 'false'
os.environ.setdefault('EXPORT_DIR', '/tmp/test_export')
os.environ.setdefault('OUTPUT_DIR', '/tmp/test_output')

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
parse_path = os.path.join(src_path, 'parse')
# As in test_model_bones: 'parse' must be the src/parse package, not src/parse/parse.py
if not hasattr(sys.modules.get('parse'), '__path__'):
    parse_pkg = types.ModuleType('parse')
    parse_pkg.__path__ = [parse_path]
    sys.modules['parse'] = parse_pkg
sys.path.insert(0, src_path)
sys.path.insert(0, parse_path)

from parsers import map as map_parser  # noqa: E402

CONTENT = os.path.join("WRFrontiers", "Content", "Sparrow")


def _queued(key):
    return {"Key": key, "Value": {"TableId": "/Game/Sparrow/Localization/ST_MapNames.ST_MapNames", "Key": f"Map_{key}",
                                  "SourceString": key, "LocalizedString": key}}


def _sublevels(*suffixes, hidden=()):
    return [{"Suffix": f"_{suffix}", "bMandatory": False, "bVisible": suffix not in hidden, "bBlocking": True}
            for suffix in suffixes]


class TestMapParser(unittest.TestCase):
    def setUp(self):
        self.export_dir = tempfile.mkdtemp()
        self._write(os.path.join(CONTENT, "UI", "Meta", "QueueModes", "DataAssets", "DA_QueueCommonData.json"), [{
            "Type": "SQueueModesCommonDataAsset",
            "Properties": {"MapsLocalization": [_queued("Mont"), _queued("EM1")], "GameModesLocalization": []},
        }])
        self._write(os.path.join(CONTENT, "Localization", "ST_MapNames.json"), [{
            "Type": "StringTable",
            "StringTable": {"TableNamespace": "MapNames", "KeysToEntries": {"Map_Mont": "Fissure", "Map_Tutorial": "PIT"}},
        }])
        self._bp("SpearHead/BP_GameMode_Spearhead.json", _sublevels("Spearhead", "PostCombat", "Crusher", hidden=("PostCombat",)))
        self._bp("Beacon/BP_GameMode_Beacon.json", _sublevels("BeaconRush", "PostCombat", hidden=("PostCombat",)))
        self._bp("Beacon/BP_GameMode_BeaconOnboarding.json", _sublevels("BeaconRush"))
        self._bp("FiringRange/BP_GameMode_FiringRange.json", None)

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def _write(self, relative_file, data):
        file = os.path.join(self.export_dir, relative_file)
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file)

    def _bp(self, relative_file, sublevels):
        properties = {"SubLevels": sublevels} if sublevels is not None else {"WinScore": 1}
        self._write(os.path.join(CONTENT, "GameModes", relative_file),
                    [{"Type": "BlueprintGeneratedClass"}, {"Type": "Default__X_C", "Properties": properties}])

    def test_map_entries_queued_then_named_then_unnamed(self):
        entries = map_parser.map_entries(self.export_dir)
        self.assertEqual(list(entries), ["Mont", "EM1", "Tutorial", "FiringRange"])
        self.assertEqual([entry["queued"] for entry in entries.values()], [True, True, False, False])
        self.assertEqual(entries["Tutorial"]["localization"], {"TableId": map_parser.MAP_NAMES_TABLE_ID, "Key": "Map_Tutorial"})
        self.assertIsNone(entries["FiringRange"]["localization"])

    def test_map_entries_need_queued_maps(self):
        self._write(os.path.join(CONTENT, "UI", "Meta", "QueueModes", "DataAssets", "DA_QueueCommonData.json"), [{
            "Type": "SQueueModesCommonDataAsset", "Properties": {"MapsLocalization": []}}])
        with self.assertRaises(ValueError):
            map_parser.map_entries(self.export_dir)

    def test_game_mode_sublevels_are_the_visible_ones(self):
        self.assertEqual(map_parser.game_mode_sublevels(self.export_dir),
                         {"BeaconRush": ["BeaconRush"], "Spearhead": ["Spearhead", "Crusher"]})


if __name__ == '__main__':
    unittest.main()
