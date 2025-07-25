# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import parse_hex
from parsers.image import parse_badge_visual_info, parse_image_asset_path
from parsers.localization_table import parse_localization

class Faction(Object):
    objects = dict()  # Dictionary to hold all Faction instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Image": (parse_image_asset_path, "image_path"),
            "Name": parse_localization,
            "BadgeVisualInfo": (parse_badge_visual_info, "badge"),
            "Color": (parse_hex, "hex"),  # Directly set color to the value
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)