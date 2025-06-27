# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import parse_localization

class Rarity(Object):
    objects = dict()  # Dictionary to hold all Rarity instances
    
    def _parse(self):
        props = self.source_data["Properties"]
        rarity_info = props["RarityInfo"]

        key_to_parser_function = {
            "Name": (parse_localization, "name"),
            "RarityColor": (self._p_hex, "hex"),
        }

        self._process_key_to_parser_function(key_to_parser_function, rarity_info, 2)

    def _p_hex(self, data):
        return data["Hex"]
