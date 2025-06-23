# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from utils import parse_localization, log

class ModuleCategory(Object):
    objects = dict()  # Dictionary to hold all ModuleCategory instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": self._p_human_name,
            "Description": self._p_description,
            "TutorialTargetTag": None,
            "Icon": self._p_icon,
            "SuperCategory": None,
            "SortOrder": self._p_sort_order,
            "IsVisual": self._p_is_visual,
            "ModuleTypeUIStats": self._p_ui_stats,
            "RingErrorText": None,
            "UIStats": self._p_ui_stats,
        }
        for key, data in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function:
                    function(data)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'", tabs=2)

    def _p_human_name(self, data):
        self.name = parse_localization(data)

    def _p_description(self, data):
        self.description = parse_localization(data)

    def _p_icon(self, data):
        pass #TODO

    def _p_sort_order(self, data):
        self.sort_order = data

    def _p_is_visual(self, data):
        self.is_visual = data

    def _p_ui_stats(self, data):
        pass #TODO