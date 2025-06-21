# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.rarity import Rarity
from utils import path_to_id, log, get_json_data, asset_path_to_file_path

class ModuleRarity(Object):
    objects = dict()  # Dictionary to hold all ModuleRarity instances
    
    def _parse(self):
        props = self.source_data["Properties"]
        self.sort_order = props["SortOrder"]

        rarity_asset_path = props["RarityDataAsset"]["ObjectPath"]
        self.rarity_id = Rarity.get_from_asset_path(rarity_asset_path)