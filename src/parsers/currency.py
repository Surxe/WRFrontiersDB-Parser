# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path

from utils import parse_hex

class Currency(Object):
    objects = dict()  # Dictionary to hold all ModuleStat instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"),
            "Description": parse_localization,
            "HowToUseDescriptions": self._parse_localizations,
            "WhereToGetDescriptions": self._parse_localizations,
            "WalletIcon": (parse_image_asset_path, "wallet_icon_path"),
            "LargeIcon": (parse_image_asset_path, "large_icon_path"),
            "BackgroundColor": parse_hex,
            "BackgroundImage": (parse_image_asset_path, "background_image_path"),
            "CurrencyType": None,
            "PaymentSoundEvent": None,
            "GroupReward": None,
            "CurrencyMesh": None,
            "CustomRangesVisual": None,
            "ShopDisplayPriority": "value",  # Directly set priority to the value
            "NotEnoughBehavior": None,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _parse_localizations(self, list):
        parsed_localizations = []
        for elem in list:
            parsed_localizations.append(parse_localization(elem))
        return parsed_localizations
    
def parse_currency(data):
    """
    data may contain 
    {
        "Currency": { ObjectPath: object path to Currency },
        "Amount": int
    }

    returns
    {
        "currency_id": Currency
        "Amount": int
    }
    """
    if "Currency" not in data or "Amount" not in data:
        return None
    
    currency_data = data["Currency"]
    current_amount = data["Amount"]

    if currency_data is None and current_amount == 0:
        return None
    elif currency_data is None:
        raise Exception(f"Structure change: {self.__class__.__name__} {self.id} has currency data with no Currency but Amount is {current_amount} and length of array is {len(data)}.", tabs=1)
    
    currency_asset_path = currency_data["ObjectPath"]
    currency_id = Currency.get_from_asset_path(currency_asset_path)

    return {
        "currency_id": currency_id,
        "amount": current_amount
    }