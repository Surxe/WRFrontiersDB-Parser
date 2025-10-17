# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path
from parsers.module_stat import ModuleStat

class ModuleCategory(ParseObject):
    objects = dict()  # Dictionary to hold all ModuleCategory instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "TutorialTargetTag": None,
            "Icon": (parse_image_asset_path, "icon_path"),
            "SuperCategory": None,
            "SortOrder": "value",
            "IsVisual": "value",
            "ModuleTypeUIStats": (self._p_type_ui_stats, "module_type_ui_stats"),
            "RingErrorText": None,
            "UIStats": (self._p_ui_stats, "ui_stats"),
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_ui_stats(self, data):
        ids = []
        for elem in data:
            ids.append(ModuleStat.get_from_asset_path(elem["ObjectPath"]))
        return ids
    
    def _p_type_ui_stats(self, data):
        from parsers.module_type import ModuleType

        parsed = []
        for elem in data:
            stat_id = ModuleStat.get_from_asset_path(elem["ModuleStat"]["ObjectPath"])
            module_type_id = ModuleType.get_from_asset_path(elem["ModuleType"]["ObjectPath"], create_if_missing=False) #must always avoid creating module types at this point as it will recursively search for a module category and recursion loop. Module categories can be parsed thru another source to avoid infinite loop
            parsed.append({
                'module_stat_id': stat_id,
                'module_type_id': module_type_id
            })

        return parsed
