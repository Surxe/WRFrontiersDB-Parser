# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class UpgradeCost(ParseObject):
    objects = dict()  # Dictionary to hold all UpgradeCost instances

    def __init__(self, module_id, level_num, currency_id, amount):
        id = f"{module_id}_level{level_num}_cost"
        super().__init__(id, {
            "module_id": module_id,
            "level_num": level_num,
            "currency_id": currency_id,
            "amount": amount
        })
        
    def _parse(self):
        self.module_id = self.source_data.get("module_id")
        self.level_num = self.source_data.get("level_num")
        self.currency_id = self.source_data.get("currency_id")
        self.amount = self.source_data.get("amount")