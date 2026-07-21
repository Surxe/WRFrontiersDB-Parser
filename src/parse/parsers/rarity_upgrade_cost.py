import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class RarityUpgradeCost(ParseObject):
    objects = dict()

    def __init__(self, id: str, rarity_ref: str, costs: dict):
        self.id = id
        self.rarity_ref = rarity_ref
        self.costs = costs
        
        self.objects[id] = self

    def _parse(self):
        pass
