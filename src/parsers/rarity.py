# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

class Rarity(Object):
    objects = dict()  # Dictionary to hold all ModuleRarity instances
    localization_table_id = None

    def _parse(self):
        props = self.source_data["Properties"]
        rarity_info = props["RarityInfo"]
        self.localization_key = rarity_info["Name"]["Key"]
        if Rarity.localization_table_id is None:
            Rarity.localization_table_id = rarity_info["Name"]["TableId"].split("/")[-1].split(".")[0]
        self.hex = rarity_info["RarityColor"]["Hex"]