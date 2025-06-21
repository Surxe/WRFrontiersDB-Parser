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
        self.name = parse_localization(rarity_info["Name"])
        self.hex = rarity_info["RarityColor"]["Hex"]