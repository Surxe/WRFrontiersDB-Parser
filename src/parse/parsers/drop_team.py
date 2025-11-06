# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.factory_preset import FactoryPreset

class DropTeam(ParseObject):
    objects = dict()  # Dictionary to hold all DropTeam instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Characters": self._p_characters,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_characters(self, data):
        ids = []
        for elem in data:
            preset_id = FactoryPreset.get_from_asset_path(elem["ObjectPath"])
            ids.append(preset_id)
        return ids