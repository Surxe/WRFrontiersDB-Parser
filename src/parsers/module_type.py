# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.module_category import ModuleCategory
from utils import parse_localization, parse_hex, parse_colon_colon

class ModuleType(Object):
    objects = dict()  # Dictionary to hold all ModuleType instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Category": (self._p_module_category, "module_category_id"),
            "HumanName": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "BlueprintName": (parse_localization, "blueprint_name"),
            "TagColor": (parse_hex, "tag_color"),
            "TagBackgroundColor": (parse_hex, "tag_background_color"),
            "ModuleSocketTypes": None,
            "IsRootModule": ("value", "is_root_module"),
            "CharacterType": (parse_colon_colon, "character_type"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)

    def _p_module_category(self, data):
        asset_path = data["ObjectPath"]

        return ModuleCategory.get_from_asset_path(asset_path)