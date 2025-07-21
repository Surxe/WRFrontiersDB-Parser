# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.localization_table import parse_localization
from parsers.image import parse_badge_visual_info

class PilotClass(Object):
    objects = dict()  # Dictionary to hold all PilotClass instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": parse_localization,
            "BadgeVisualInfo": (parse_badge_visual_info, "badge"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)