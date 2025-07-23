# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import path_to_id
from parsers.object import Object
from parsers.currency import Currency, parse_currency
from parsers.content_unlock import ContentUnlock
from parsers.decal import Decal
from parsers.customization_type import CustomizationType
from parsers.customization_rarity import CustomizationRarity
from parsers.rarity import Rarity
from parsers.image import Image
from parsers.group_reward import GroupReward
from parsers.material import Material

class ProgressionTable(Object):
    objects = dict()  # Dictionary to hold all ProgressionTable instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Levels": self._p_levels,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_levels(self, levels: list):
        parsed_levels = dict()

        for i, level in enumerate(levels):
            level_number = i+1
            key_to_parser_function = {
                "ReputationCost": "value",
                "Reward": (self._p_level_reward, "rewards")
            }

            parsed_level = self._process_key_to_parser_function(key_to_parser_function, level, set_attrs=False, log_descriptor='_p_levels()', tabs=3)
            parsed_levels[level_number] = parsed_level

        return parsed_levels

    def _p_level_reward(self, reward: dict):
        key_to_parser_function = {
            "Currencies": (lambda currencies: [parse_currency(currency) for currency in currencies], "currencies"),
            "ContentUnlocks": (lambda content_unlocks: [ContentUnlock.get_from_asset_path(content_unlock["ObjectPath"]) for content_unlock in content_unlocks], "content_unlocks_ids"),
            "CharacterModules": (self._p_modules, "modules"),
            "Decals": (lambda decals: [Decal.get_from_asset_path(decal["Decal"]["ObjectPath"]) for decal in decals], "decals_ids"),
            "Materials": (lambda materials: [Material.get_from_asset_path(material["Material"]["ObjectPath"]) for material in materials], "materials_ids"),
            "GlobalDecals": self._p_global_decals,
            "Weathering": self._p_confirm_empty,
            #TODO
        }

        parsed_reward = self._process_key_to_parser_function(key_to_parser_function, reward, set_attrs=False, log_descriptor='_p_level_reward()', tabs=4)
        
        # Remove empty lists and dicts
        parsed_reward = {k: v for k, v in parsed_reward.items() if v not in ([], {}, None)}

        return parsed_reward
    
    def _p_modules(self, data: list):
        parsed_ms = []
        for element in data:
            parsed_m = dict()
            module_id = path_to_id(element["Module"]["ObjectPath"])
            parsed_m["module_id"] = module_id
            parsed_m["level"] = element["Level"]
            parsed_ms.append(parsed_m)
        return parsed_ms
    
    def _p_confirm_empty(self, data: list):
        if data != []:
            raise ValueError("Data structure change, ProgressionTable level attribute is no longer always empty.")

def parse_progression_table():
    progression_table_path = r"WRFrontiers/Content/Sparrow/Mechanics/DA_ProgressionTable.json"

    # Hero pilots are in this dir directly
    progression_table = ProgressionTable.get_from_asset_path(progression_table_path)

    ProgressionTable.to_file()
    Currency.to_file()
    ContentUnlock.to_file()
    Decal.to_file()
    CustomizationType.to_file()
    CustomizationRarity.to_file()
    Rarity.to_file()
    GroupReward.to_file()
    Material.to_file()

    Image.to_file()

if __name__ == "__main__":
    parse_progression_table()