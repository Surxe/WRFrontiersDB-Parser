# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import path_to_id
from parsers.object import Object
from parsers.currency import Currency, parse_currency
from parsers.content_unlock import ContentUnlock

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
            "CharacterModules": (self._p_character_modules, "modules"),
            #TODO
        }

        parsed_reward = self._process_key_to_parser_function(key_to_parser_function, reward, set_attrs=False, log_descriptor='_p_level_reward()', tabs=4)
        
        # Remove empty lists and dicts
        parsed_reward = {k: v for k, v in parsed_reward.items() if v not in ([], {}, None)}

        return parsed_reward
    
    def _p_character_modules(self, data: list):
        parsed_ms = []
        for element in data:
            parsed_m = dict()
            module_id = path_to_id(element["Module"]["ObjectPath"])
            parsed_m["module_id"] = module_id
            parsed_m["level"] = element["Level"]
            parsed_ms.append(parsed_m)
        return parsed_ms

def parse_progression_table():
    progression_table_path = r"WRFrontiers/Content/Sparrow/Mechanics/DA_ProgressionTable.json"

    # Hero pilots are in this dir directly
    progression_table = ProgressionTable.get_from_asset_path(progression_table_path)

    ProgressionTable.to_file()
    Currency.to_file()
    ContentUnlock.to_file()

if __name__ == "__main__":
    parse_progression_table()