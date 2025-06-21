# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from utils import parse_localization, log

class ModuleSocketType(Object):
    objects = dict()  # Dictionary to hold all ModuleSocketType instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": self._p_human_name,
            "HumanShortName": self._p_human_short_name,
            "Icon": self._p_icon,
            "ShowInConstructor": None,
            "ListPriority": None,
            "TagColor": self._p_tag_color,
            "TagBackgroundColor": self._p_tag_background_color,
            "TutorialTargetTag": None,
            "RingErrorText": None,
            "FilterOptions": None,
            "SortingOptions": None,
            "CompatibleModules": self._p_compatible_modules,
            "ID": None,
        }
        for key, data in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function:
                    function(data)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'", tabs=3)

    def _p_human_name(self, data):
        self.name = parse_localization(data)

    def _p_human_short_name(self, data):
        self.short_name = parse_localization(data)

    def _p_icon(self, data):
        pass #TODO

    def _p_description(self, data):
        self.description = parse_localization(data)

    def _p_tag_color(self, data):
        self.tag_color = data["Hex"]

    def _p_tag_background_color(self, data):
        self.tag_background_color = data["Hex"]

    def _p_compatible_modules(self, data):
        pass

    def _p_icon(self, data):
        pass #TODO