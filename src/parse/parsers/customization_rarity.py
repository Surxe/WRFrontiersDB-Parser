# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization
from parsers.customization_type import CustomizationType
from parsers.rarity import Rarity

class CustomizationRarity(ParseObject):
    objects = dict()  # Dictionary to hold all CustomizationRarity instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "RarityDataAsset": (self._p_rarity, "rarity_ref"), 
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_rarity(self, data):
        return Rarity.create_from_asset(data).to_ref()