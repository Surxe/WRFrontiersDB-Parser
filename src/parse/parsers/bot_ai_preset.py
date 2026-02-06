# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, get_json_data, OPTIONS

from parsers.object import ParseObject
from parsers.drop_team import DropTeam
from parsers.character_preset import CharacterPreset
from parsers.league import League
from parsers.image import Image

class BotAIPreset(ParseObject):
    objects = dict()

    def _parse(self):
        props = self.source_data["Properties"]["Preset"]
        
        key_to_parser_function = {
            "SkillRate": "value",
            "LevelInterval": "value",
            "DropTeams": (self._p_drop_teams, "drop_teams_refs"),
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_drop_teams(self, data):
        refs = []
        for elem in data:
            drop_team_ref = DropTeam.create_from_asset(elem).to_ref()
            refs.append(drop_team_ref)
        return refs

def parse_bot_ai_presets(to_file=False):
    root_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path, index=0)
    props = root_data["Properties"]

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
        bot_preset = BotAIPreset.create_from_asset(bot_preset_entry["Value"])
        # Ensure it doesn't already have a level
        if hasattr(bot_preset, "levels"):
            bot_preset.levels.append(level)
        else:
            bot_preset.levels = [level]
    
    # parse the league-array
    for bot_preset_entry in bot_presets_by_league:
        league_asset_path = bot_preset_entry["Key"]
        logger.debug(f"Found league path {league_asset_path}")
        league_ref = League.create_from_asset_path(league_asset_path).to_ref() # Just to validate it exists
        bot_preset = BotAIPreset.create_from_asset(bot_preset_entry["Value"])
        # Ensure it doesn't already have a league
        if hasattr(bot_preset, "league_refs"):
            bot_preset.league_refs.append(league_ref)
        else:
            bot_preset.league_refs = [league_ref]

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        BotAIPreset.to_file()
        DropTeam.to_file()
        CharacterPreset.to_file()
        League.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_bot_ai_presets(to_file=True)