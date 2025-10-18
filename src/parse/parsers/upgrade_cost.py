# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class UpgradeCost(ParseObject):
    objects = dict()  # Dictionary to hold all UpgradeCost instances

    def __init__(self, id, currency_id, amount):
        super().__init__(id, {
            "currency_id": currency_id,
            "amount": amount
        })
        
    def _parse(self):
        self.currency_id = self.source_data.get("currency_id")
        self.amount = self.source_data.get("amount")