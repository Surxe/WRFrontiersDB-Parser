# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class UpgradeCost(ParseObject):
    objects = dict()  # Dictionary to hold all UpgradeCost instances

    def _make_unique_id(self, id_to_try, currency_id, amount):
        other_obj = self.objects.get(id_to_try, None)
        if other_obj is not None:
            # Get the others values
            other_currency_id = other_obj.source_data.get("currency_id")
            other_amount = other_obj.source_data.get("amount")
            
            # Check if they match mine
            if other_currency_id == currency_id and other_amount == amount:
                # Reuse the existing object
                return id_to_try
            
            else:
                # Conflict, try a longer id
                return None
        
        else: # object doesnt yet exist, so use it
            return id_to_try

    def __init__(self, level_num, module_rarity, currency_id, amount):
        try_id2 = f"{level_num}_{module_rarity}_{currency_id}"
        id = self._make_unique_id(try_id2, currency_id, amount)
        if id is None:
            try_id3 = f"{level_num}_{module_rarity}_{currency_id}_{amount}"
            id = self._make_unique_id(try_id3, currency_id, amount)

        super().__init__(id, {
            "level_num": level_num,
            "module_rarity_id": module_rarity,
            "currency_id": currency_id,
            "amount": amount
        }, can_override=False)
        
    def _parse(self):
        self.module_rarity_id = self.source_data.get("module_rarity_id")
        self.level_num = self.source_data.get("level_num")
        self.currency_id = self.source_data.get("currency_id")
        self.amount = self.source_data.get("amount")