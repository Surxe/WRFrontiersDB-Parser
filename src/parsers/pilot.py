# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, asset_path_to_data, parse_colon_colon, PARAMS
from parsers.localization_table import parse_localization

from parsers.object import Object
from parsers.faction import Faction
from parsers.currency import Currency, parse_currency
from parsers.image import parse_image_asset_path, Image

class Pilot(Object):
    objects = dict()

    def _parse(self):
        props = self.source_data[0]["Properties"]
        
        key_to_parser_function = {
            "FirstName": (parse_localization, "first_name"),
            "SecondName": (self._p_second_name, None),
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
            "SellPrice": (parse_currency, "sell_price"),
            "Levels": (self._p_levels, "levels"), #
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)

    def _p_second_name(self, data: dict):
        second_name = parse_localization(data)
        if second_name["InvariantString"] != " ":
            log(f"Data structure changed for {self.__class__.__name__} {self.id}, second_name is not empty: {second_name['InvariantString']}", tabs=1)
        return

    def _p_pilot_blueprint(self, data: dict): #TODO
        pass

    def _p_pilot_type(self, data: dict):
        pass

    def _p_pilot_class(self, data: dict):
        pass

    def _p_personality(self, data: dict):
        pass

    def _p_faction(self, data: dict):
        asset_path = data["ObjectPath"]
        return Faction.get_from_asset_path(asset_path, log_tabs=1)
    
    def _p_sell_price(self, data: dict):
        return {
            "currency_id": Currency.get_from_asset_path(data["Currency"]["ObjectPath"], log_tabs=1),
            "Amount": data["Amount"]
        }
    
    def _p_levels(self, data: dict):
        # Placeholder for future implementation
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
    Faction.to_file()
    Currency.to_file()

if __name__ == "__main__":
    parse_pilots()