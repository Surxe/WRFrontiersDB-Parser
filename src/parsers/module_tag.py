# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import parse_hex
from parsers.localization_table import parse_localization

class ModuleTag(Object):
    objects = dict()  # Dictionary to hold all ModuleTag instances
    
    def _parse(self):
        props = self.source_data["Properties"]
        
        key_to_parser_function = {
            "HumanName": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "TextColor": (parse_hex, "text_hex"),
            "BackgroundColor": (parse_hex, "background_hex"),
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props, 2)
