# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path

class ModuleCategory(Object):
    objects = dict()  # Dictionary to hold all ModuleCategory instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "TutorialTargetTag": None,
            "Icon": (parse_image_asset_path, "icon_path"),
            "SuperCategory": None,
            "SortOrder": ("value", "sort_order"),
            "IsVisual": ("value", "is_visual"),
            "ModuleTypeUIStats": (self._p_ui_stats, "module_type_ui_stats"),
            "RingErrorText": None,
            "UIStats": (self._p_ui_stats, "ui_stats"),
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_ui_stats(self, data):
        pass #TODO