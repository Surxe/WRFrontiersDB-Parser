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
            "Characters": (self._p_characters, "character_presets_refs"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_characters(self, data):
        refs = []
        for elem in data:
            preset_ref = CharacterPreset.create_from_asset(elem).to_ref()
            refs.append(preset_ref)
        return refs