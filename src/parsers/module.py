# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, asset_path_to_data, parse_colon_colon, PARAMS
from parsers.localization_table import parse_localization

from parsers.object import Object
from parsers.module_rarity import ModuleRarity
from parsers.rarity import Rarity
from parsers.character_module import CharacterModule
from parsers.ability import Ability
from parsers.faction import Faction
from parsers.module_class import ModuleClass
from parsers.character_class import CharacterClass
from parsers.module_tag import ModuleTag
from parsers.module_type import ModuleType
from parsers.module_category import ModuleCategory
from parsers.module_socket_type import ModuleSocketType
from parsers.module_stat import ModuleStat
from parsers.module_stats_table import ModuleStatsTable
from parsers.currency import Currency, parse_currency
from parsers.image import parse_image_asset_path, Image

class Module(Object):
    objects = dict()
    
    def _parse(self): #Sparrow\Mechanics\Meta\Entities\Modules\DA_Module_ChassisRaven.json
        for elem in self.source_data:
            if elem["Type"] != "SCharacterModuleDataAsset":
                continue

            # Parse properties
            props = elem["Properties"]

            # {k: v} if k is a key in props, parse it with the corresponding function
            key_to_parser_function = {
                "ProductionStatus": (parse_colon_colon, "production_status"),
                "IsUniversalMounted": None,
                "InventoryIcon": (parse_image_asset_path, "inventory_icon_path"),
                "ModuleRarity": (self._p_module_rarity, "module_rarity_id"),
                "CharacterModules": (self._p_character_modules, "character_module_mounts"),
                "ModuleTags": (self._p_module_tags, "module_tags_ids"),
                "ModuleScaler": (self._p_module_scalar, None),
                "AbilityScalers": (self._p_ability_scalars, None),
                "Title": (parse_localization, "name"),
                "Description": (parse_localization, "description"),
                "TextTags": (self._p_text_tags, "text_tags"),
                "Faction": (self._p_faction, "faction_id"),
                "ModuleClasses": (self._p_module_classes, "module_classes_ids"),
                "PreviewVideoPath": None,
                "ModuleStatsTable": (self._p_module_stats_table, "module_stats_table_id"),
                "ModuleType": (self._p_module_type, "module_type_id"),
                "Sockets": (self._p_sockets, "module_socket_type_ids"),
                "Levels": (self._p_levels, None),
                "ID": None,
            }
            
            self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

        if not hasattr(self, "production_status"):
            log(f"Module {self.id} is not ready for production", tabs=1)

    def _p_module_rarity(self, data):
        asset_path = data["ObjectPath"]
        return ModuleRarity.get_from_asset_path(asset_path)

    def _p_character_modules(self, data):
        character_module = dict()
        character_module_mounts = []
        asset_path_name = None
        for character_module in data:
            new_asset_path_name = character_module["Value"]["AssetPathName"]
            character_module_mounts.append(parse_colon_colon(character_module["Key"]))  # "ESCharacterModuleMountWay::Left" -> Left

            # Confirm that all character modules have the same asset path name
            if asset_path_name is not None and new_asset_path_name != asset_path_name:
                raise Exception(f"Data structure change: {self.__class__.__name__} {self.id} character module data has more than one character module file ")
            
            character_module_id = CharacterModule.get_from_asset_path(new_asset_path_name)

        return {
            "id": character_module_id,
            "mounts": character_module_mounts,
        }
                
    def _p_module_tags(self, data):
        module_tags = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            module_tag_id = ModuleTag.get_from_asset_path(asset_path)
            module_tags.append(module_tag_id)
        return module_tags

    def _p_module_scalar(self, data):
        module_scalar_data = asset_path_to_data(data["ObjectPath"])
        if not hasattr(self, "levels"):
            self.levels = dict()
        self.levels["module_scalars"] = self._p_scalars(module_scalar_data)
        
    def _p_ability_scalars(self, data):
        self.levels["abilities_scalars"] = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            ability_scalar_data = asset_path_to_data(asset_path)
            self.levels["abilities_scalars"].append(self._p_scalars(ability_scalar_data))

    def _p_scalars(self, data):
        if "LevelsData" not in data["Properties"]:
            return
        
        def _p_parameter(data, parmeter_order):
            """
            data may contain 
            {
                "DefaultPrimaryParameter": float,
                "PrimaryStatMetaInformation": { ObjectPath: object path to ModuleStat }
            }
            parameter_order = "Primary" or "Secondary"
            """
            default_x_parameter = f"Default{parmeter_order}Parameter"
            x_stat_meta_information = f"{parmeter_order}StatMetaInformation"
            if x_stat_meta_information in data:
                asset_path = data[x_stat_meta_information]["ObjectPath"]
                stat_id = ModuleStat.get_from_asset_path(asset_path)
                return stat_id
            
        parsed_scalars = dict()
        parsed_scalars["constants"] = dict()  # {constant_key: value}
        stat1 = _p_parameter(data["Properties"], "Primary")
        stat2 = _p_parameter(data["Properties"], "Secondary")
        if stat1 is not None:
            if hasattr(self, "primary_stat_id") and stat1 != self.primary_stat_id:
                log(f"Warning: {self.__class__.__name__} {self.id} has different primary stat ID {stat1} than previously parsed {self.primary_stat_id}.", tabs=1)
            self.primary_stat_id = stat1

        if stat2 is not None:
            if hasattr(self, "secondary_stat_id") and stat2 != self.secondary_stat_id:
                log(f"Warning: {self.__class__.__name__} {self.id} has different secondary stat ID {stat2} than previously parsed {self.secondary_stat_id}.", tabs=1)
            self.secondary_stat_id = stat2

        parsed_levels_data = self._p_levels_data(data["Properties"]["LevelsData"])

        constants_and_variables = self._separate_constants_and_variables(parsed_levels_data)
        parsed_scalars["constants"] = constants_and_variables["constants"]
        parsed_scalars["variables"] = constants_and_variables["variables"]

        return parsed_scalars
    
    def _p_levels_data(self, data):
        parsed_levels = []
        for level in data:
            """
            level may contain:
            {
                "UpgradeCurrency": "DA_Meta_Currency_Alloys",
                "UpgradeCost": 51200,
                
                "FirstScrapRewardAmount": 15360,
                "FirstScrapRewardCurrency": "DA_Meta_Currency_Alloys",
                "SecondScrapRewardAmount": 0,
                "SecondScrapRewardCurrency": "DA_Meta_Currency_Intel",
            }
            """

            parsed_level = dict()

            if "UpgradeCurrency" in level and "UpgradeCost" in level:
                upgrade_currency = level["UpgradeCurrency"]
                upgrade_cost = level["UpgradeCost"]
                if upgrade_currency is not None and upgrade_cost > 0:
                    parsed_level["UpgradeCurrency"] = {
                        "currency_id": upgrade_currency,
                        "amount": upgrade_cost
                    }

            def _p_scrap_reward_amount(first_or_second):
                """
                first_or_second: "First" or "Second"
                """
                scrap_reward_amount_key = f"{first_or_second}ScrapRewardAmount"
                scrap_reward_currency_key = f"{first_or_second}ScrapRewardCurrency"
                if scrap_reward_currency_key in level and scrap_reward_amount_key in level:
                    scrap_reward_currency = level[scrap_reward_currency_key]
                    scrap_reward_amount = level[scrap_reward_amount_key]
                    if scrap_reward_currency is not None and scrap_reward_amount > 0:
                        parsed_level['ScrapRewards'].append({
                            "currency_id": scrap_reward_currency,
                            "amount": scrap_reward_amount
                        })
                

            parsed_level["ScrapRewards"] = []
            _p_scrap_reward_amount("First")
            _p_scrap_reward_amount("Second")

            # Include all other key data pairs in the level
            for key, value in level.items():
                if key not in ["UpgradeCurrency", "UpgradeCost", "FirstScrapRewardAmount", "FirstScrapRewardCurrency", "SecondScrapRewardAmount", "SecondScrapRewardCurrency"]:
                    parsed_level[key] = value

            parsed_levels.append(parsed_level)

        return parsed_levels

    def _separate_constants_and_variables(self, levels_data):
        """
        Separates constants and variables from the data.
        Constants are those that do not change across levels.
        Variables are those that change across levels.
        """
        
        # Determine which stats are constants and which are not
        first_level_data = levels_data[0]
        non_constants = dict() # {non_constant_key: True}
        for level in levels_data[1:]: # iterate levels starting from i=1
            for key, value in level.items():
                if key in first_level_data and first_level_data[key] != value:
                    non_constants[key] = True
                
        parsed_levels_variable_stats = [] # [levels] where level = {variable_stat_key: value}
        parsed_constant_stats = dict() # {constant_stat_key: value}
        for i, level in enumerate(levels_data):
            parsed_level_variable_stats = dict()
            for key, value in level.items():
                if i == 0 and key not in non_constants: # if it's the first level and it's a constant, add it to parsed_constant_stats
                    parsed_constant_stats[key] = value
                if key in non_constants: # if it's not a constant, add it to parsed_level_variable_stats
                    parsed_level_variable_stats[key] = level[key]

            parsed_levels_variable_stats.append(parsed_level_variable_stats)

        return {
            "variables": parsed_levels_variable_stats,
            "constants": parsed_constant_stats
        }

    def _p_text_tags(self, data):
        text_tags = []
        for elem in data:
            tag_localization = parse_localization(elem)
            text_tags.append(tag_localization)
        return text_tags

    def _p_faction(self, data):
        asset_path = data["ObjectPath"]
        return Faction.get_from_asset_path(asset_path, log_tabs=1)

    def _p_module_classes(self, data):
        module_classes_ids = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            module_class_id = ModuleClass.get_from_asset_path(asset_path)
            module_classes_ids.append(module_class_id)
        return module_classes_ids

    def _p_module_stats_table(self, data):
        asset_path = data["ObjectPath"]
        return ModuleStatsTable.get_from_asset_path(asset_path)     

    def _p_module_type(self, data):
        asset_path = data["ObjectPath"]
        return ModuleType.get_from_asset_path(asset_path, log_tabs=1)

    def _p_sockets(self, data):
        module_socket_type_ids = []
        for elem in data:
            asset_path = elem["Type"]["ObjectPath"]
            module_socket_type_id = ModuleSocketType.get_from_asset_path(asset_path)
            module_socket_type_ids.append(module_socket_type_id)
        return module_socket_type_ids

    def _p_levels(self, data):
        if not hasattr(self, "levels"):
            self.levels = dict()
        self.levels["scrap_rewards"] = {}
        self.levels["scrap_rewards"]["variables"] = []

        for index, level in enumerate(data):
            # Item is only purchaseable at level 0, so we set the price only for the first level
            if index == 0 and "Price" in level:
                price = level["Price"]
                self.price = parse_currency(price)
                
            # Add scrap rewards to its respective level
            if 'ScrapRewards' in level:
                scrap_rewards_data = level["ScrapRewards"]
                parsed_scrap_rewards = []
                for elem in scrap_rewards_data:
                    if type(elem) is dict and "Currency" in elem and "Amount" in elem:
                        parsed_elem = parse_currency(elem)
                        if parsed_elem is None:
                            return
                        parsed_scrap_rewards.append(parsed_elem)
                    else:
                        parsed_scrap_rewards.append(elem)

                self.levels["scrap_rewards"]["variables"].append(parsed_scrap_rewards)


def parse_modules(to_file=False):
    modules_source_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Mechanics\Meta\Entities\Modules")
    for file in os.listdir(modules_source_path):
        if file.endswith(".json"):
            full_path = os.path.join(modules_source_path, file)
            module_id = path_to_id(file)
            log(f"Parsing {Module.__name__} {module_id} from {full_path}", tabs=0)
            module_data = get_json_data(full_path)
            module = Module(module_id, module_data)

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        Module.to_file()
        ModuleRarity.to_file()
        Rarity.to_file()
        CharacterModule.to_file()
        Faction.to_file()
        ModuleClass.to_file()
        CharacterClass.to_file()
        ModuleTag.to_file()
        ModuleType.to_file()
        ModuleCategory.to_file()
        ModuleSocketType.to_file()
        ModuleStat.to_file()
        ModuleStatsTable.to_file()
        Currency.to_file()
        Ability.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_modules(to_file=True)