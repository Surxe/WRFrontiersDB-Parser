# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, path_to_id, get_json_data, asset_to_data, OPTIONS
from parsers.localization_table import parse_localization

from parsers.object import ParseObject
from parsers.faction import Faction
from parsers.currency import Currency, parse_currency
from parsers.image import Image, parse_image_asset_path
from parsers.pilot_type import PilotType
from parsers.rarity import Rarity
from parsers.group_reward import GroupReward
from parsers.pilot_class import PilotClass
from parsers.pilot_personality import PilotPersonality
from parsers.pilot_talent_type import PilotTalentType
from parsers.pilot_talent import PilotTalent
from parsers.module_stat import ModuleStat
from parsers.module_tag import ModuleTag

class Pilot(ParseObject):
    objects = dict()

    def _parse(self):
        props = self.source_data[0]["Properties"]
        
        key_to_parser_function = {
            "FirstName": (parse_localization, "first_name"),
            "SecondName": (self._p_second_name, "second_name"),
            "Image": (parse_image_asset_path, "image_path"),
            "VoiceSwitch": None,
            "PilotBlueprint": None,
            "Bio": (parse_localization, "bio"),
            "ReactionSet": None,
            "HangarReactionSet": None,
            "PilotSkin": None,
            "Rarity": (self._p_pilot_type, "pilot_type_id"),
            "PilotClass": (self._p_pilot_class, "pilot_class_id"),
            "Personality": (self._p_personality, "personality_id"),
            "Faction": (self._p_faction, "faction_id"),
            "SellPrice": (parse_currency, "sell_price"),
            "Levels": (self._p_levels, "levels"), #
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_second_name(self, data: dict):
        second_name = parse_localization(data)
        if 'InvariantString' in second_name and second_name["InvariantString"] == " ":
            return # if last name is a space, ignore it
        return second_name

    def _p_pilot_type(self, data: dict):
        return PilotType.create_from_asset(data).to_ref()

    def _p_pilot_class(self, data: dict):
        return PilotClass.create_from_asset(data).to_ref()

    def _p_personality(self, data: dict):
        return PilotPersonality.create_from_asset(data).to_ref()

    def _p_faction(self, data: dict):
        return Faction.create_from_asset(data).to_ref()
    
    def _p_sell_price(self, data: dict):
        return {
            "currency_id": Currency.create_from_asset(data["Currency"]).to_ref(),
            "Amount": data["Amount"]
        }
    
    def _p_levels(self, levels: list):
        self.levels = []

        expected_rep_costs = [None, 1000, 2000, 5000, 10000]

        logger.debug(f"Parsing {len(levels)} levels for {self.id}")

        for i, level in enumerate(levels):
            level_data = asset_to_data(level)
            if level_data is None:
                raise ValueError(f"Level data not found for asset: {level}")
            self.levels.append(dict())
        
            props = level_data["Properties"]
            self.levels[i]["talent_type_id"] = PilotTalentType.create_from_asset(props["TalentType"]).to_ref()
            if "ReputationCost" in props:
                rep_cost = props["ReputationCost"]
                expected_rep_cost = expected_rep_costs[i]
                if rep_cost != expected_rep_cost:
                    logger.error(f"Reputation cost for {self.id} level {i} is {rep_cost}, expected {expected_rep_cost} for frontend purposes")
                self.levels[i]["reputation_cost"] = rep_cost
            upgrade_cost = parse_currency(props["CurrencyCost"])
            if upgrade_cost:
                self.levels[i]["upgrade_cost"] = upgrade_cost
            talents = props["Talents"]
            self.levels[i]["talents"] = []
            for talent in talents:
                talent_id = PilotTalent.create_from_asset(talent).to_ref()
                self.levels[i]["talents"].append(talent_id)

def parse_pilot_wrapper(dir, file_name):
    if not file_name.endswith(".json"):
        return
    full_path = os.path.join(dir, file_name)
    pilot_id = path_to_id(file_name)
    logger.debug(f"Parsing {Pilot.__name__} {pilot_id} from {full_path}")
    pilot_data = get_json_data(full_path)
    pilot = Pilot(pilot_id, pilot_data)
    return pilot

def parse_pilots(to_file=False):
    pilots_source_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Pilots\PilotsDataAssets")
    
    # Hero pilots are in this dir directly
    for file in os.listdir(pilots_source_path):
        if file == 'DA_Pilot_FiringRange.json':
            continue # guessing this is used as a placeholder when in the firing range, it has dummy values
        pilot = parse_pilot_wrapper(pilots_source_path, file)

    # Common pilots are in a subdir:
    common_pilots_path = os.path.join(pilots_source_path, "CommonPilots")
    for file in os.listdir(common_pilots_path):
        pilot = parse_pilot_wrapper(common_pilots_path, file)

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        Pilot.to_file()
        Faction.to_file()
        Currency.to_file()
        PilotType.to_file()
        Rarity.to_file()
        GroupReward.to_file()
        PilotClass.to_file()
        PilotPersonality.to_file()
        PilotTalentType.to_file()
        PilotTalent.to_file()
        ModuleStat.to_file()
        ModuleTag.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_pilots(to_file=True)