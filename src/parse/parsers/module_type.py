# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.module_category import ModuleCategory
from utils import parse_hex, parse_colon_colon
from parsers.localization_table import parse_localization

class ModuleType(ParseObject):
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

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_module_category(self, data):
        return ModuleCategory.create_from_asset(data).to_ref()