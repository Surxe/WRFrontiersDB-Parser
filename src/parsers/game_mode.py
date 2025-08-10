# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, asset_path_to_file_path, asset_path_to_data, PARAMS
from parsers.localization_table import parse_localization

from parsers.object import Object
from parsers.image import Image

class GameMode(Object):
    objects = dict()

    def _parse(self):
        props = self.source_data[0]["Properties"]
        
        key_to_parser_function = {
            "DisplayName": parse_localization,
            "Description": parse_localization,
            "Icon": None, #the icon may be an Engine asset, which is not downloaded
            "Name": None, #non-localized name
            "ID": None
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _parse_bp(self, bp_path: str):
        bp_data = get_json_data(bp_path)
        cdo_path = bp_data[0]["ClassDefaultObject"]["ObjectPath"]
        cdo_data = asset_path_to_data(cdo_path)
        props = cdo_data["Properties"]

        key_to_parser_function = {
            "GameMode": None,
            "Map": None,
            "MaxPlayers": None,
            "MinPlayers": None
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

def parse_game_modes(to_file=False):
    root_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path)
    game_modes = root_data[0]["Properties"]["GameModes"]
    for game_mode_entry in game_modes:
        game_mode_asset_path = game_mode_entry["ObjectPath"]
        game_mode_id = path_to_id(game_mode_asset_path)
        game_mode_file_path = asset_path_to_file_path(game_mode_asset_path)
        game_mode_data = get_json_data(game_mode_file_path)

        # Only parse gamemodes that have a localized display name, these are actual game modes. Others include Hangar, tutorial, title menu, or even just list of bot names
        if 'Properties' in game_mode_data[0]:
            if 'DisplayName' in game_mode_data[0]['Properties']:
                if 'CultureInvariantString' not in game_mode_data[0]['Properties']["DisplayName"]:
                    log(f"Parsing {GameMode.__name__} {game_mode_id} from {game_mode_file_path}", tabs=0)
                    game_mode = GameMode(game_mode_id, game_mode_data)

    # Manually map to the game mode setting file, which is separate to the name & description container file, and only connected server side
    game_mode_id_to_bp_path = {
        "DA_GameMode_BeaconRush": r"GameModes\Beacon\BP_GameMode_Beacon.json",
        "DA_GameMode_Elimination": r"GameModes\Elimination\BP_GameMode_Elimination.json",
        "DA_GameMode_TeamDeathMatch": r"GameModes\TeamDeathMatch\BP_GameMode_TeamDeathMatch.json",
        "DA_GameMode_Spearhead": r"GameModes\Spearhead\BP_GameMode_Spearhead.json"
    }

    for game_mode_id, bp_path in game_mode_id_to_bp_path.items():
        game_mode = GameMode.objects.get(game_mode_id)
        if game_mode:
            game_mode._parse_bp(os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow", bp_path))

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        GameMode.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_game_modes(to_file=True)