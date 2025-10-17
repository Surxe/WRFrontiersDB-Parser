# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path

class PilotPersonality(ParseObject):
    objects = dict()  # Dictionary to hold all PilotPersonality instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Icon": (parse_image_asset_path, "icon_path"),
            "Name": parse_localization,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)