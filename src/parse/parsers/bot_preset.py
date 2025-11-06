# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, get_json_data, OPTIONS

from parsers.object import ParseObject
from parsers.drop_team import DropTeam
from parsers.factory_preset import FactoryPreset
from parsers.league import League
from parsers.image import Image

class BotPreset(ParseObject):
    objects = dict()

    def _parse(self):
        props = self.source_data["Properties"]["Preset"]
        
        key_to_parser_function = {
            "SkillRate": "value",
            "LevelInterval": "value",
            "DropTeams": self._p_drop_teams,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_drop_teams(self, data):
        ids = []
        for elem in data:
            drop_team_id = DropTeam.get_from_asset_path(elem["ObjectPath"])
            ids.append(drop_team_id)
        return ids

def parse_bot_presets(to_file=False):
    root_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path)
    props = root_data[0]["Properties"]

    # Older version only has by-level in BotPresets
    # Newer version (as of 2025-09-09) has both by-level and by-league
    if "BotPresets" in props:
        bot_presets_by_level = props["BotPresets"]
        bot_presets_by_league = []
    elif "DedicatedBotPresets" in props:
        bot_presets_by_level = props["DedicatedBotPresets"]["BotPresetsByLevel"]
        bot_presets_by_league = props["DedicatedBotPresets"]["BotPresetByLeague"]
    else:
        raise ValueError("Neither 'BotPresets' nor 'DedicatedBotPresets' found in root properties.")
    
    for bot_preset_entry in bot_presets_by_level:
        level = bot_preset_entry["Key"]
        bot_preset_asset_path = bot_preset_entry["Value"]["ObjectPath"]
        bot_preset_id = BotPreset.get_from_asset_path(bot_preset_asset_path)
        # Ensure it doesn't already have a level
        bot_preset = BotPreset.objects[bot_preset_id]
        if hasattr(bot_preset, "levels"):
            bot_preset.levels.append(level)
        else:
            bot_preset.levels = [level]
    
    # parse the league-array
    for bot_preset_entry in bot_presets_by_league:
        league_asset_path = bot_preset_entry["Key"]
        logger.debug(f"Found league path {league_asset_path}")
        league_id = League.get_from_asset_path(league_asset_path) # Just to validate it exists
        league_id = league_id #placeholder
        bot_preset_asset_path = bot_preset_entry["Value"]["ObjectPath"]
        bot_preset_id = BotPreset.get_from_asset_path(bot_preset_asset_path)
        # Ensure it doesn't already have a league
        bot_preset = BotPreset.objects[bot_preset_id]
        if hasattr(bot_preset, "league_ids"):
            bot_preset.league_ids.append(league_id)
        else:
            bot_preset.league_ids = [league_id]

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        BotPreset.to_file()
        DropTeam.to_file()
        FactoryPreset.to_file()
        League.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_bot_presets(to_file=True)