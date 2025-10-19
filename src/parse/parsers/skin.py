# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization
from parsers.customization_rarity import CustomizationRarity

class Skin(ParseObject):
    objects = dict()  # Dictionary to hold all Skin instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "SkinName": (parse_localization, "name"),
            "SkinDescription": (parse_localization, "description"),
            "SkinIcon": (parse_image_asset_path, "icon_path"),
            "Skin": None, #lists decals, materials, weathering etc.. Not worth parsing
            "Rarity": (self._p_customization_rarity, "customization_rarity_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_customization_rarity(self, data):
        if data is None:
            return
        return CustomizationRarity.get_from_asset_path(data["ObjectPath"])