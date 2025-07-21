# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path

class PilotTalentType(Object):
    objects = dict()  # Dictionary to hold all PilotTalentType instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": parse_localization,
            "Description": parse_localization,
            "Image": (parse_image_asset_path, "image_path"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)