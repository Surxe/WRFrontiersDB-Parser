# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.character_class import CharacterClass

class ModuleClass(Object):
    objects = dict()  # Dictionary to hold all ModuleClass instances
    
    def _parse(self):
        props = self.source_data["Properties"]
        character_class_asset_path = props["CharacterClassDataAsset"]["ObjectPath"]
        CharacterClass.get_from_asset_path(character_class_asset_path)