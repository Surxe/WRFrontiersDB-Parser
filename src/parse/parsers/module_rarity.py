# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.rarity import Rarity

class ModuleRarity(ParseObject):
    objects = dict()  # Dictionary to hold all ModuleRarity instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "SortOrder": "value",
            "RarityDataAsset": (self._p_rarity_data_asset, "rarity_id"),
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_rarity_data_asset(self, data):
        asset_path = data["ObjectPath"]
        return Rarity.get_from_asset_path(asset_path)