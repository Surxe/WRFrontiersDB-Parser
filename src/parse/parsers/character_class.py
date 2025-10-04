# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.image import parse_badge_visual_info, parse_image_asset_path
from parsers.localization_table import parse_localization

class CharacterClass(Object):
    objects = dict()  # Dictionary to hold all Class instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "BadgeVisualInfo": (parse_badge_visual_info, "badge"),
            "ImageBig": (parse_image_asset_path, "image_big_path"),
            "ImageSmall": (parse_image_asset_path, "image_small_path"),
            "Name": parse_localization,
            "Description": "value",
            "Priority": None,
            "TutorialTag": None,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)
