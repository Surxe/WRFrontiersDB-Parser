# Add two levels of parent dirs to sys path
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.image import parse_image_asset_path, Image
from utils import OPTIONS, get_json_data, parse_colon_colon

class ShopCard(ParseObject):
    objects = dict()  # Dictionary to hold all ShopCard instances

    def _parse(self):
        props = self.source_data.get("Properties", {})

        key_to_parser_function = {
            "Size": self._parse_size,
            "Backgrounds": self._parse_backgrounds,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _parse_size(self, data):
        self.width = data.get("X")
        self.height = data.get("Y")

    def _parse_backgrounds(self, data):
        backgrounds = []
        for entry in data:
            raw_value = entry.get("Value")
            if raw_value:
                image_path = parse_image_asset_path(raw_value)
                backgrounds.append(image_path)
        self.backgrounds = backgrounds

def parse_shop_cards(to_file=False):
    file_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\UI\Screens\Offers\WBP_CommonOfferCard.json")
    
    if not os.path.exists(file_path):
        return

    data = get_json_data(file_path)
    
    # Find the default object
    default_obj = None
    for item in data:
        if item.get("Type") == "WBP_CommonOfferCard_C" and item.get("Name", "").startswith("Default__"):
            default_obj = item
            break
            
    if not default_obj:
        return
        
    props = default_obj.get("Properties", {})
    card_sizes = props.get("CardSizes", [])
    
    for entry in card_sizes:
        enum_key = entry.get("Key")
        asset_ref = entry.get("Value")
        
        if enum_key and asset_ref:
            shop_card = ShopCard.create_from_asset(asset_ref)
            if shop_card:
                if not getattr(shop_card, "backgrounds", None):
                    if shop_card.id in ShopCard.objects:
                        del ShopCard.objects[shop_card.id]
                else:
                    shop_card.size_type = parse_colon_colon(enum_key)

    if to_file:
        ShopCard.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_shop_cards(to_file=True)
