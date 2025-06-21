# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.rarity import Rarity
from utils import asset_path_to_data

class CharacterModule(Object):
    objects = dict()  # Dictionary to hold all CharacterModule instances
    
    def _parse(self):
        class_default_object = self.source_data["ClassDefaultObject"]
        cdo_data = asset_path_to_data(class_default_object["ObjectPath"])
        props = cdo_data["Properties"]
        pass