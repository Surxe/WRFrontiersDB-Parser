# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization
from parsers.customization_type import CustomizationType
from parsers.customization_rarity import CustomizationRarity

class Weathering(Object):
    objects = dict()  # Dictionary to hold all Weathering instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "WeatheringName": (parse_localization, "name"),
            "WeatheringDescription": (parse_localization, "description"),
            "WeatheringIcon": (parse_image_asset_path, "icon_path"),
            "Type": (self._p_customization_type, "customization_type_id"),
            "WeatheringParams": None,
            "Rarity": (self._p_customization_rarity, "customization_rarity_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_customization_rarity(self, data):
        return CustomizationRarity.get_from_asset_path(data["ObjectPath"])
    
    def _p_customization_type(self, data):
        return CustomizationType.get_from_asset_path(data["ObjectPath"])