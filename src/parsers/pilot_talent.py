# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path

class PilotTalent(Object):
    objects = dict()  # Dictionary to hold all PilotTalent instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "UIDescription": (parse_localization, "ui_description"),
            "ShortUIDescription": (parse_localization, "short_ui_description"),
            "Image": (parse_image_asset_path, "image_path"),
            "PilotTalent": (self._p_bp, "placeholder"), #TODO
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)

    def _p_placeholder(self, data: dict): #TODO
        pass