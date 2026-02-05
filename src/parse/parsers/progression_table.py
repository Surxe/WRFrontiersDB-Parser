# Add parent dirs to sys path
import sys
import os

from loguru import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import path_to_id, asset_to_asset_path
from parsers.object import ParseObject
from parsers.currency import Currency, parse_currency
from parsers.content_unlock import ContentUnlock
from parsers.decal import Decal
from parsers.customization_type import CustomizationType
from parsers.customization_rarity import CustomizationRarity
from parsers.rarity import Rarity
from parsers.image import Image
from parsers.group_reward import GroupReward
from parsers.material import Material
from parsers.weathering import Weathering
from parsers.skin import Skin
from parsers.module import Module
from parsers.pilot import Pilot

class ProgressionTable(ParseObject):
    objects = dict()  # Dictionary to hold all ProgressionTable instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Levels": self._p_levels,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_levels(self, levels: list):
        parsed_levels = dict()

        for i, level in enumerate(levels):
            level_number = i+1
            key_to_parser_function = {
                "ReputationCost": "value",
                "Reward": (self._p_level_reward, "rewards")
            }

            parsed_level = self._process_key_to_parser_function(key_to_parser_function, level, set_attrs=False, log_descriptor='_p_levels()')
            parsed_levels[level_number] = parsed_level

        return parsed_levels

    def _p_level_reward(self, reward: dict):
        key_to_parser_function = {
            "ReputationPoints": self._confirm_0,
            "Currencies": (lambda currencies: [parse_currency(currency) for currency in currencies], "currencies"),
            "CharacterModules": (self._p_modules, "modules"),
            "Blueprints": (lambda blueprints: [Module.create_from_asset(blueprint).to_ref() for blueprint in blueprints], "blueprints_ids"),
            "Characters": self._confirm_empty,
            "ContentUnlocks": (lambda content_unlocks: [ContentUnlock.create_from_asset(content_unlock).to_ref() for content_unlock in content_unlocks], "content_unlocks_ids"),
            "Premium": self._confirm_empty,
            "Decals": (lambda decals: [Decal.create_from_asset(decals["Decal"]).to_ref() for decals in decals], "decals_ids"),
            "Materials": (lambda materials: [Material.create_from_asset(material["Material"]).to_ref() for material in materials], "materials_ids"),
            "GlobalDecals": self._confirm_empty,
            "Weathering": (lambda weathering: [Weathering.create_from_asset(weather["Weathering"]).to_ref() for weather in weathering], "weatherings_ids"),
            "CharacterSkins": (lambda skins: [Skin.create_from_asset(skin["Skin"]).to_ref() for skin in skins], "skins_ids"),
            "CharacterSetups": self._confirm_empty,
            "PilotRewards": (self._p_pilots, "pilots"),
            "ModuleVariantRewards": self._confirm_empty,
            "RobotVariantRewards": self._confirm_empty,
        }

        parsed_reward = self._process_key_to_parser_function(key_to_parser_function, reward, set_attrs=False, log_descriptor='_p_level_reward()')
        
        # Remove empty lists and dicts
        parsed_reward = {k: v for k, v in parsed_reward.items() if v not in ([], {}, None)}

        return parsed_reward
    
    def _p_modules(self, data: list):
        parsed_ms = []
        for element in data:
            parsed_m = dict()
            module_id, _ = Module.get_from_asset(element["Module"])
            parsed_m["module_id"] = module_id
            parsed_m["level"] = element["Level"]
            parsed_ms.append(parsed_m)
        return parsed_ms
    
    def _p_pilots(self, data: list):
        parsed_pilots = []
        for element in data:
            parsed_p = dict()
            pilot_id, _ = Pilot.get_from_asset(element["Pilot"])
            parsed_p["pilot_id"] = pilot_id
            parsed_p["level"] = element["Level"]
            parsed_pilots.append(parsed_p)
        return parsed_pilots
    
    def _confirm_empty(self, data: list):
        if data != []:
            logger.error(f"Data structure change, ProgressionTable level attribute is no longer always empty. {data}")

    def _confirm_0(self, data: int):
        if data != 0:
            logger.error(f"Data structure change, ProgressionTable level attribute is no longer always 0.")

def parse_progression_table(to_file=False):
    progression_table_path = r"WRFrontiers/Content/Sparrow/Mechanics/DA_ProgressionTable.json"

    # Hero pilots are in this dir directly
    progression_table = ProgressionTable.create_from_asset_path(progression_table_path)

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        ProgressionTable.to_file()
        Currency.to_file()
        ContentUnlock.to_file()
        Decal.to_file()
        CustomizationType.to_file()
        CustomizationRarity.to_file()
        Rarity.to_file()
        GroupReward.to_file()
        Material.to_file()
        Weathering.to_file()
        Skin.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_progression_table(to_file=True)