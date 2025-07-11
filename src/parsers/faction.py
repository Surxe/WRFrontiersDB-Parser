# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import path_to_id, parse_hex
from parsers.image import parse_badge_visual_info
from parsers.localization_table import parse_localization

class Faction(Object):
    objects = dict()  # Dictionary to hold all Faction instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Image": (self._p_image, "image_id"),
            "Name": (parse_localization, "name"),
            "BadgeVisualInfo": (parse_badge_visual_info, "badge"),
            "Color": (parse_hex, "hex"),  # Directly set color to the value
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)

    def _p_image(self, data):
        """
        Parses the image data and returns the image ID.
        """
        return path_to_id(data["AssetPathName"])