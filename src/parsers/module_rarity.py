# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.rarity import Rarity
from utils import path_to_id, log, get_json_data, asset_path_to_file_path

class ModuleRarity(Object):
    objects = dict()  # Dictionary to hold all ModuleRarity instances
    localization_table_id = None

    def _parse(self):
        props = self.source_data["Properties"]
        self.sort_order = props["SortOrder"]

        rarity_asset_path = props["RarityDataAsset"]["ObjectPath"]
        self.rarity_id = path_to_id(rarity_asset_path)
        rarity = Rarity.get_from_id(self.rarity_id)
        if rarity is None:
            file_path = asset_path_to_file_path(rarity_asset_path)
            log(f"Parsing {Rarity.__name__} {self.rarity_id} from {file_path}", tabs=2)
            rarity_data = get_json_data(file_path)[0]
            rarity = Rarity(self.rarity_id, rarity_data)