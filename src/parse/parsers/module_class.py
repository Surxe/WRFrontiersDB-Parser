# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.character_class import CharacterClass

class ModuleClass(ParseObject):
    objects = dict()  # Dictionary to hold all ModuleClass instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "CharacterClassDataAsset": (self._p_character_class, "character_class_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_character_class(self, data):
        asset_path = data["ObjectPath"]
        return CharacterClass.get_from_asset_path(asset_path)