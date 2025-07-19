# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, asset_path_to_data, parse_colon_colon, PARAMS
from parsers.localization_table import parse_localization

from parsers.object import Object
from parsers.image import parse_image_asset_path, Image

class Pilot(Object):
    objects = dict()

    def _parse(self):
        props = self.source_data[0]["Properties"]
        
        key_to_parser_function = {
            "FirstName": (parse_localization, "first_name"),
            "SecondName": (parse_localization, "second_name"),
            "Image": (parse_image_asset_path, "image_path"),
            "VoiceSwitch": None,
            "PilotBlueprint": (self._p_pilot_blueprint, "pilot_blueprint_id"),
            "Bio": (parse_localization, "bio"),
            "ReactionSet": None,
            "HangarReactionSet": None,
            "PilotSkin": None,
            "Rarity": (self._p_pilot_type, "pilot_type_id"),
            "PilotClass": (self._p_pilot_class, "pilot_class_id"),
            "Personality": (self._p_personality, "personality_id"),
            "Faction": (self._p_faction, "faction_id"),
            "SellPrice": None, #TODO
            "Levels": None, #TODO
            "ID": None,
        }

    def _p_pilot_blueprint(self, data: dict): #TODO
        pass

    def _p_pilot_type(self, data: dict):
        pass

    def _p_pilot_class(self, data: dict):
        pass

    def _p_personality(self, data: dict):
        pass

    def _p_faction(self, data: dict):
        pass

def parse_pilots():
    pilots_source_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Pilots\PilotsDataAssets\CommonPilots")
    for file in os.listdir(pilots_source_path):
        if file.endswith(".json"):
            full_path = os.path.join(pilots_source_path, file)
            pilot_id = path_to_id(file)
            log(f"Parsing {Pilot.__name__} {pilot_id} from {full_path}", tabs=0)
            pilot_data = get_json_data(full_path)
            pilot = Pilot(pilot_id, pilot_data)

    Pilot.to_file()

if __name__ == "__main__":
    parse_pilots()