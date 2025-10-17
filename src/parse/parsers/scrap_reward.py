# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class ScrapReward(ParseObject):
    objects = dict()  # Dictionary to hold all ScrapReward instances

    def __init__(self, level_num, currency_id, amount):
        id = f"{level_num}_{currency_id}_{amount}"
        super().__init__(id, {
            "level_num": level_num,
            "currency_id": currency_id,
            "amount": amount
        })
        
    def _parse(self):
        #self.module_rarity_id = self.source_data.get("module_rarity_id")
        self.level_num = self.source_data.get("level_num")
        self.currency_id = self.source_data.get("currency_id")
        self.amount = self.source_data.get("amount")