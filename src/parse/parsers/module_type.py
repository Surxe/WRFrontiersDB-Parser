# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.module_category import ModuleCategory
from utils import parse_hex, parse_colon_colon
from parsers.localization_table import parse_localization

class ModuleType(Object):
    objects = dict()  # Dictionary to hold all ModuleType instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Category": (self._p_module_category, "module_category_id"),
            "HumanName": (parse_localization, "name"),
            "Description": parse_localization,
            "BlueprintName": parse_localization,
            "TagColor": (parse_hex, "tag_color"),
            "TagBackgroundColor": parse_hex,
            "ModuleSocketTypes": None,
            "IsRootModule": "value",
            "CharacterType": parse_colon_colon,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_module_category(self, data):
        asset_path = data["ObjectPath"]

        return ModuleCategory.get_from_asset_path(asset_path)