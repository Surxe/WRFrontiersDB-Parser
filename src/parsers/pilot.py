# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, asset_path_to_data, PARAMS
from parsers.localization_table import parse_localization

from parsers.object import Object
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

class Pilot(Object):
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

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_second_name(self, data: dict):
        second_name = parse_localization(data)
        if 'InvariantString' in second_name and second_name["InvariantString"] == " ":
            return # if last name is a space, ignore it
        return second_name

    def _p_pilot_type(self, data: dict):
        return PilotType.get_from_asset_path(data["ObjectPath"], log_tabs=1)

    def _p_pilot_class(self, data: dict):
        return PilotClass.get_from_asset_path(data["ObjectPath"], log_tabs=1)

    def _p_personality(self, data: dict):
        return PilotPersonality.get_from_asset_path(data["ObjectPath"], log_tabs=1)

    def _p_faction(self, data: dict):
        asset_path = data["ObjectPath"]
        return Faction.get_from_asset_path(asset_path, log_tabs=1)
    
    def _p_sell_price(self, data: dict):
        return {
            "currency_id": Currency.get_from_asset_path(data["Currency"]["ObjectPath"], log_tabs=1),
            "Amount": data["Amount"]
        }
    
    def _p_levels(self, levels: list):
        self.levels = []

        log(f"Parsing {len(levels)} levels for {self.id}", tabs=1)

        for i, level in enumerate(levels):
            level_data = asset_path_to_data(level["ObjectPath"])
            if level_data is None:
                log(f"Failed to get level data for {self.id} from {level['ObjectPath']}", tabs=1)
                continue
            self.levels.append(dict())
        
            props = level_data["Properties"]
            self.levels[i]["talent_type_id"] = PilotTalentType.get_from_asset_path(props["TalentType"]["ObjectPath"], log_tabs=2)
            if "ReputationCost" in props:
                self.levels[i]["reputation_cost"] = props["ReputationCost"]
            self.levels[i]["upgrade_cost"] = parse_currency(props["CurrencyCost"])
            talents = props["Talents"]
            self.levels[i]["talents"] = []
            for talent in talents:
                asset_path = talent["ObjectPath"]
                talent_id = PilotTalent.get_from_asset_path(asset_path, log_tabs=2)
                self.levels[i]["talents"].append(talent_id)

            # Process the level data as needed
            #self.levels[i] = level_data

def parse_pilot_wrapper(dir, file_name):
    if not file_name.endswith(".json"):
        return
    full_path = os.path.join(dir, file_name)
    pilot_id = path_to_id(file_name)
    log(f"Parsing {Pilot.__name__} {pilot_id} from {full_path}", tabs=0)
    pilot_data = get_json_data(full_path)
    pilot = Pilot(pilot_id, pilot_data)
    Pilot.objects[pilot_id] = pilot
    return pilot

def parse_pilots(to_file=False):
    pilots_source_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Pilots\PilotsDataAssets")
    
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