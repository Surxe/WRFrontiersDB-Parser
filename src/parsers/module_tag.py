# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import parse_localization

class ModuleTag(Object):
    objects = dict()  # Dictionary to hold all ModuleTag instances
    
    def _parse(self):
        props = self.source_data["Properties"]
        
        self.name = parse_localization(props["HumanName"])
        if 'Description' in props:
            description = parse_localization(props["Description"])
            if description is not None:
                self.description = description
        self.text_hex = props["TextColor"]["Hex"]
        self.background_hex = props["BackgroundColor"]["Hex"]