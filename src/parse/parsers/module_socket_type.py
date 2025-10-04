# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.module_type import ModuleType
from utils import parse_hex
from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path

class ModuleSocketType(Object):
    objects = dict()  # Dictionary to hold all ModuleSocketType instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"),
            "HumanShortName": (parse_localization, "short_name"),
            "Icon": (parse_image_asset_path, "icon_path"),
            "ShowInConstructor": None,
            "ListPriority": None,
            "TagColor": parse_hex,
            "TagBackgroundColor": parse_hex,
            "TutorialTargetTag": None,
            "RingErrorText": None,
            "FilterOptions": None,
            "SortingOptions": None,
            "bCanBeChangedByUser": "value",
            "CompatibleModules": (self._p_compatible_modules, "compatible_module_types_ids"),
            "Required": "value",
            "ID": None,
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_compatible_modules(self, data):
        compatible_module_types = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            module_type_id = ModuleType.get_from_asset_path(asset_path)
            compatible_module_types.append(module_type_id)
        
        return compatible_module_types