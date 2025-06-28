# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.localization_table import parse_localization

class Currency(Object):
    objects = dict()  # Dictionary to hold all ModuleStat instances
    
    def _parse(self):
        props = self.source_data["Properties"]
        pass

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "WalletIcon": (self._p_icon, "wallet_icon"),
            "LargeIcon": (self._p_icon, "large_icon"),
            "CurrencyType": None,
            "PaymentSoundEvent": None,
            "GroupReward": None,
            "CurrencyMesh": None,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)

    def _p_icon(self, data):
        """
        Parses the icon data from the source data.
        This method should be implemented to handle the specific icon parsing logic.
        """
        pass