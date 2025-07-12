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
            "Description": (parse_localization, "description"),
            "WalletIcon": (parse_image_asset_path, "wallet_icon_path"),
            "LargeIcon": (parse_image_asset_path, "large_icon_path"),
            "BackgroundColor": (parse_hex, "background_color"),
            "BackgroundImage": (parse_image_asset_path, "background_image_path"),
            "CurrencyType": None,
            "PaymentSoundEvent": None,
            "GroupReward": None,
            "CurrencyMesh": None,
            "CustomRangesVisual": None,
            "ShopDisplayPriority": ("value", "shop_display_priority"),  # Directly set priority to the value
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, 2)