# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import parse_badge_visual_info, parse_localization

class CharacterClass(Object):
    objects = dict()  # Dictionary to hold all Class instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "BadgeVisualInfo": (parse_badge_visual_info, "badge"),
            "Name": (parse_localization, "name"),
            "Description": ("value", "description"),  # Directly set description to the value
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)
        