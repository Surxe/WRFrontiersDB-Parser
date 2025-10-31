# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, path_to_id, get_json_data, asset_path_to_data, parse_colon_colon, OPTIONS
from parsers.localization_table import parse_localization

from parsers.object import ParseObject
from parsers.module_rarity import ModuleRarity
from parsers.rarity import Rarity
from parsers.character_module import CharacterModule, get_default_key_to_parser_function
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
from parsers.currency import Currency
from parsers.upgrade_cost import UpgradeCost
from parsers.scrap_reward import ScrapReward
from parsers.image import parse_image_asset_path, Image

class Module(ParseObject):
    objects = dict()
    
    def _parse(self): #Sparrow\Mechanics\Meta\Entities\Modules\DA_Module_ChassisRaven.json
        # Parse properties
        props = self.source_data["Properties"]

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
            "Levels": None,
            "ID": None,
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props)

        if not hasattr(self, "production_status"):
            logger.debug(f"Module {self.id} is not ready for production")

    def _p_module_rarity(self, data):
        asset_path = data["ObjectPath"]
        return ModuleRarity.get_from_asset_path(asset_path)

    def _p_character_modules(self, data):
        character_modules = []
        for character_module in data:
            new_asset_path_name = character_module["Value"]["AssetPathName"]
            mount = parse_colon_colon(character_module["Key"]) # "ESCharacterModuleMountWay::Left" -> Left
            character_module_id = CharacterModule.get_from_asset_path(new_asset_path_name)
            character_modules.append({
                "character_module_id": character_module_id,
                "mount": mount,
            })

        return character_modules
                
    def _p_module_tags(self, data):
        module_tags = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            module_tag_id = ModuleTag.get_from_asset_path(asset_path)
            module_tags.append(module_tag_id)
        return module_tags

    def _p_module_scalar(self, data):
        module_scalar_data = asset_path_to_data(data["ObjectPath"])
        scalars = self._p_scalars(module_scalar_data)
        if not scalars:
            return
        self.module_scalars = scalars
        

    def _p_ability_scalars(self, data):
        for elem in data:
            asset_path = elem["ObjectPath"]
            ability_scalar_data = asset_path_to_data(asset_path)
            scalars = self._p_scalars(ability_scalar_data)
            if not scalars:
                continue

            if not hasattr(self, "abilities_scalars"):
                self.abilities_scalars = []
            self.abilities_scalars.append(scalars)

    def _p_scalars(self, data):
        key_to_parser_function = {
            "LevelsData": (self._p_levels_data, "levels"),
            "PrimaryStatMetaInformation": (self._p_parameter, "primary_stat_id"),
            "SecondaryStatMetaInformation": (self._p_parameter, "secondary_stat_id"),
            "ModuleName": None,
            "bAllowStatsReporting": None,
        }
        key_to_parser_function.update(get_default_key_to_parser_function())
        parsed_scalars = self._process_key_to_parser_function(key_to_parser_function, data["Properties"], set_attrs=False, log_descriptor="Scalars")
        
        # Determine which stats need to be inverted (reciprocal taken of) based on if the stat has unit_exponent -1
        primary_stat_id = parsed_scalars.pop("primary_stat_id", None)
        invert_primary = False
        invert_secondary = False
        if primary_stat_id is not None:
            primary_stat = ModuleStat.get_from_id(primary_stat_id)
            invert_primary = primary_stat is not None and getattr(primary_stat, "unit_exponent", None) == -1
        secondary_stat_id = parsed_scalars.pop("secondary_stat_id", None)
        if secondary_stat_id is not None:
            secondary_stat = ModuleStat.get_from_id(secondary_stat_id)
            invert_secondary = secondary_stat is not None and getattr(secondary_stat, "unit_exponent", None) == -1
        
        # Reciprocal PrimaryParameter and SecondaryParameter in level data
        if invert_primary or invert_secondary:
            levels_data = parsed_scalars.get("levels", {})
            def invert(level):
                if invert_primary and "PrimaryParameter" in level:
                    level["PrimaryParameter"] = 1 / level["PrimaryParameter"]
                if invert_secondary and "SecondaryParameter" in level:
                    level["SecondaryParameter"] = 1 / level["SecondaryParameter"]
            for level in levels_data.get("variables", []):
                invert(level)
            if "constants" in levels_data:
                invert(levels_data["constants"])
            

        ret = dict()
        for key, value in parsed_scalars.items():
            if key in ["levels", "primary_stat_id", "secondary_stat_id"]:
                ret[key] = value
            else:
                if "default_scalars" not in ret:
                    ret["default_scalars"] = dict()
                ret["default_scalars"][key] = value

        return ret

    def _p_parameter(self, data):
        return ModuleStat.get_from_asset_path(data["ObjectPath"])
    
    def _p_levels_data(self, data):
        module_rarity = self.module_rarity_id if hasattr(self, "module_rarity_id") else None
        if module_rarity is None:
            logger.warning(f"Warning: Module {self.id} level {level_num} is missing module_rarity_id")

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

                "Level": 1,
            }
            """
            level_num = level["Level"]

            parsed_level = dict()


            # Parse upgrade and scrap currencies
            module_lvl_id = f"{self.id}_lvl{level_num}"
            if "UpgradeCurrency" in level and "UpgradeCost" in level:
                upgrade_currency = level["UpgradeCurrency"]
                upgrade_cost_amount = level["UpgradeCost"]
                
                # consciously not excluding 0 amounts, as it messes up ability to check if its a constant or a variable
                if upgrade_currency is not None and upgrade_currency != "None": #it may be None if its say a torso ability module, as the ability is not what costs currency to upgrade, rather the module its attached to (torso) will have the cost
                    upgrade_cost = UpgradeCost(module_lvl_id, upgrade_currency, upgrade_cost_amount) 
                    parsed_level["upgrade_cost_id"] = upgrade_cost.id

            scrap_rewards_ids = []
            def p_scrap_reward_amount(first_or_second):
                """
                first_or_second: "First" or "Second"
                """
                scrap_reward_amount_key = f"{first_or_second}ScrapRewardAmount"
                scrap_reward_currency_key = f"{first_or_second}ScrapRewardCurrency"
                if scrap_reward_currency_key in level and scrap_reward_amount_key in level:
                    scrap_reward_currency = level[scrap_reward_currency_key]
                    scrap_reward_amount = level[scrap_reward_amount_key]
                    if scrap_reward_currency is not None and scrap_reward_currency != "None": # consciously not excluding 0 amounts, as it messes up ability to check if its a constant or a variable
                        scrap_num_id = len(scrap_rewards_ids) + 1 #index the next scrap reward will be at, +1
                        module_lvl_scrapindex_id = f"{module_lvl_id}_scrap{scrap_num_id}"
                        scrap_reward = ScrapReward(module_lvl_scrapindex_id, scrap_reward_currency, scrap_reward_amount)
                        scrap_rewards_ids.append(scrap_reward.id)

            # Since these are id'd this way, why not just have them referenced in the Module level directly?
            # A few weeks before writing, every intel discount was reflected in the client-side costs of items
            # At time of writing, it seems like they are now set server side. The last intel discount that was client side is how the data looks right now. 
            #   Meaning, ghost turret, matriarch, harpy, fuel reserve, flash bang, nanite etc. from https://warrobotsfrontiers.com/en/news/268-patch-notes-september-9-2025 are the discounted items, despite there being 4 different intel discounts since then
            # One upside of having them in their own file is for git diff categorization.
            # Maybe when I can confirm for 100% that discounts are exclusively server side, it can be reworked.
            # For now, I plan to determine the most likely upgrade costs/scrap rewards by module rarity using the most frequent values in Analysis.py
                
            p_scrap_reward_amount("First")
            p_scrap_reward_amount("Second")
            if scrap_rewards_ids:
                parsed_level["scrap_rewards_ids"] = scrap_rewards_ids


            # Parse module class and tags
            def p_module_class_tag_fac(class_or_tag, one_or_two):
                """
                class_or_tag: "Class" or "Tag" or "Faction"
                one_or_two: "1" or "2" or "0" (0 indicates no underscore will be used too)
                """
                underscore_and_number = f"_{one_or_two}" if one_or_two in ["1", "2"] else ""
                module_classtagfac_key = f"Module{class_or_tag}{underscore_and_number}"
                if module_classtagfac_key in level:
                    module_classtagfac_id = level[module_classtagfac_key]
                else:
                    logger.warning(f"Warning: Module {self.id} level {level['Level']} is missing {module_classtagfac_key}")

                if module_classtagfac_id == 'None':
                    return None

                return module_classtagfac_id
            
            def add_to_parsed_level_if_not_none(key, value):
                if value is not None:
                    parsed_level[key] = value

            add_to_parsed_level_if_not_none("module_class_id_1", p_module_class_tag_fac("Class", "1"))
            add_to_parsed_level_if_not_none("module_class_id_2", p_module_class_tag_fac("Class", "2"))
            add_to_parsed_level_if_not_none("module_tag_id_1", p_module_class_tag_fac("Tag", "1"))
            add_to_parsed_level_if_not_none("module_tag_id_2", p_module_class_tag_fac("Tag", "2"))
            add_to_parsed_level_if_not_none("module_faction_id", p_module_class_tag_fac("Faction", "0"))


            # Parse load/energy capacity
            def add_to_parsed_level_if_not_0(key, value):
                if value is not None and value != 0:
                    parsed_level[key] = value
            add_to_parsed_level_if_not_0("LoadCapacity", level.get("LoadCapacity"))
            add_to_parsed_level_if_not_0("EnergyCapacity", level.get("EnergyCapacity"))


            # Include all other key data pairs in the level
            for key, value in level.items():
                if key in ["Level", "UpgradeCurrency", "UpgradeCost", 
                           "FirstScrapRewardAmount", "FirstScrapRewardCurrency", "SecondScrapRewardAmount", "SecondScrapRewardCurrency", 
                           "ModuleClass_1", "ModuleClass_2", "ModuleTag_1", "ModuleTag_2", "ModuleFaction",
                           "LoadCapacity", "EnergyCapacity"
                           ]: #already parsed above
                    pass
                elif key in ['Health', 'Def', 'Atk', 'Mob', 'AbilityPower', 'Mobility', 'FirePower']: #flavor stats that are technically meaningless. Also not displayed anywhere as of 8-26 hangar UI changes.
                    pass
                elif key in ['bIsPerk']: #no clue what this means; its bool but can vary per level, i.e. typhon chassis lvl5 true, lvl6 false
                    pass
                else:
                    parsed_level[key] = value

            parsed_levels.append(parsed_level)

        # Categorize into constants and variables
        categorized_parsed_levels = {}
        constants_and_variables = self._separate_constants_and_variables(parsed_levels)
        constants = constants_and_variables.get("constants")
        variables = constants_and_variables.get("variables")
        if constants:
            categorized_parsed_levels["constants"] = constants
        if variables:
            categorized_parsed_levels["variables"] = variables

        return categorized_parsed_levels
    
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

            if parsed_level_variable_stats:
                parsed_levels_variable_stats.append(parsed_level_variable_stats)

        ret = {}
        if parsed_levels_variable_stats:
            ret["variables"] = parsed_levels_variable_stats
        if parsed_constant_stats:
            ret["constants"] = parsed_constant_stats
        
        return ret

    def _p_text_tags(self, data):
        text_tags = []
        for elem in data:
            tag_localization = parse_localization(elem)
            text_tags.append(tag_localization)
        return text_tags

    def _p_faction(self, data):
        asset_path = data["ObjectPath"]
        return Faction.get_from_asset_path(asset_path)

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
        return ModuleType.get_from_asset_path(asset_path)

    def _p_sockets(self, data):
        module_socket_type_ids = []
        for elem in data:
            asset_path = elem["Type"]["ObjectPath"]
            module_socket_type_id = ModuleSocketType.get_from_asset_path(asset_path)
            module_socket_type_ids.append(module_socket_type_id)
        return module_socket_type_ids
    
def find_module_element(path):
    """
    From the path to a given DA_Module_*.json file, find and return the element in the file that contains the *root* module data.
    """
    module_data = get_json_data(path)
    for i, elem in enumerate(module_data):
        if elem["Type"] != "SCharacterModuleDataAsset":
            continue
        return i, elem
    raise ValueError(f"Could not find module data in {path}")

def parse_modules(to_file=False):
    modules_source_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\Meta\Entities\Modules")
    for file in os.listdir(modules_source_path):
        if file.endswith(".json"):
            full_path = os.path.join(modules_source_path, file)
            element_index, module_element_data = find_module_element(full_path)
            # replace the index in module_id with the index of the meat and potatoes element
            file = f"{file.split('.')[0]}.{element_index}" # Cyclops.0 -> Cyclops.3 if the module data is the 4th element in the file
            module_id = path_to_id(file)
            logger.debug(f"Parsing {Module.__name__} {module_id} from {full_path}")
            module = Module(module_id, module_element_data)

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
        UpgradeCost.to_file()
        ScrapReward.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_modules(to_file=True)