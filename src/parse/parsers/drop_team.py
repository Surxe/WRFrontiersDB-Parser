# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.character_preset import CharacterPreset

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
            preset_id = CharacterPreset.get_from_asset_path(elem["ObjectPath"])
            preset = CharacterPreset.objects.get(preset_id)
            ids.append(preset_id)
        return ids