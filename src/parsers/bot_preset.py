# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_json_data, PARAMS

from parsers.object import Object
from parsers.drop_team import DropTeam
from parsers.character_preset import CharacterPreset

class BotPreset(Object):
    objects = dict()

    def _parse(self):
        props = self.source_data["Properties"]["Preset"]
        
        key_to_parser_function = {
            "SkillRate": "value",
            "LevelInterval": "value",
            "DropTeams": self._p_drop_teams,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_drop_teams(self, data):
        ids = []
        for elem in data:
            drop_team_id = DropTeam.get_from_asset_path(elem["ObjectPath"])
            ids.append(drop_team_id)
        return ids

def parse_bot_presets(to_file=False):
    root_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path)
    bot_preset = root_data[0]["Properties"]["BotPresets"]
    for bot_preset_entry in bot_preset:
        bot_preset_asset_path = bot_preset_entry["Value"]["ObjectPath"]
        bot_preset = BotPreset.get_from_asset_path(bot_preset_asset_path)

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        BotPreset.to_file()
        DropTeam.to_file()
        CharacterPreset.to_file()

if __name__ == "__main__":
    parse_bot_presets(to_file=True)