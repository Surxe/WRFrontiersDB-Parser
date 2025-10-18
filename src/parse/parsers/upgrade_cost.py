# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class UpgradeCost(ParseObject):
    objects = dict()  # Dictionary to hold all UpgradeCost instances

    def __init__(self, level_num, module_rarity, currency_id, amount):
        # Try progressively longer IDs until we find a unique one
        id_components = [
            f"{level_num}_{module_rarity}_{currency_id}",
            f"{level_num}_{module_rarity}_{currency_id}_{amount}"
        ]
        
        unique_fields = {
            "currency_id": currency_id,
            "amount": amount
        }
        
        # Generate unique ID using the utility function
        id = self._make_unique_id(id_components, unique_fields)

        super().__init__(id, {
            "level_num": level_num,
            "module_rarity_id": module_rarity,
            "currency_id": currency_id,
            "amount": amount
        }, can_override=False)
        
    def _parse(self):
        self.level_num = self.source_data.get("level_num")
        self.module_rarity_id = self.source_data.get("module_rarity_id")
        self.currency_id = self.source_data.get("currency_id")
        self.amount = self.source_data.get("amount")