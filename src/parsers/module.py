# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, parse_localization, asset_path_to_data, PARAMS

from parsers.object import Object
from parsers.module_rarity import ModuleRarity
from parsers.rarity import Rarity
from parsers.character_module import CharacterModule
from parsers.faction import Faction
from parsers.module_class import ModuleClass
from parsers.character_class import CharacterClass
from parsers.module_tag import ModuleTag
from parsers.module_type import ModuleType
from parsers.module_category import ModuleCategory
from parsers.module_socket_type import ModuleSocketType
from parsers.module_stat import ModuleStat
from parsers.module_stats_table import ModuleStatsTable

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
                "ProductionStatus": self._p_production_status,
                "IsUniversalMounted": None,
                "InventoryIcon": self._p_inventory_icon,
                "ModuleRarity": self._p_module_rarity,
                "CharacterModules": self._p_character_modules,
                "ModuleTags": self._p_module_tags,
                "ModuleScaler": self._p_module_scalar,
                "AbilityScalers": self._p_ability_scalars,
                "Title": self._p_title,
                "Description": self._p_description,
                "TextTags": self._p_text_tags,
                "Faction": self._p_faction,
                "ModuleClasses": self._p_module_classes,
                "ModuleStatsTable": self._p_module_stats_table,
                "ModuleType": self._p_module_type,
                "Sockets": self._p_sockets,
                "Levels": self._p_levels,
                "ID": None,
            }
            for key, data in props.items():
                if key in key_to_parser_function:
                    function = key_to_parser_function[key]
                    if function:
                        function(data)
                else:
                    log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'", tabs=1)
                
    
    def _p_production_status(self, data):
        self.production_status = data.split("ESCharacterModuleProductionStatus::")[-1] # "ESCharacterModuleProductionStatus::Ready" -> "Ready"
        
    def _p_inventory_icon(self, data):
        self.inventory_icon = path_to_id(data["AssetPathName"])
    
    def _p_module_rarity(self, data):
        asset_path = data["ObjectPath"]

        self.module_rarity_id = ModuleRarity.get_from_asset_path(asset_path)

    def _p_character_modules(self, data):
        self.character_module_mounts = []
        asset_path_name = None
        for character_module in data:
            new_asset_path_name = character_module["Value"]["AssetPathName"]
            self.character_module_mounts.append(character_module["Key"].split("::")[-1])  # "ESCharacterModuleMountWay::Left" -> Left

            # Confirm that all character modules have the same asset path name
            if asset_path_name is not None and new_asset_path_name != asset_path_name:
                raise Exception(f"Data structure change: {self.__class__.__name__} {self.id} character module data has more than one character module file ")
            
            CharacterModule.get_from_asset_path(new_asset_path_name)
                
    def _p_module_tags(self, data):
        self.module_tags = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            module_tag_id = ModuleTag.get_from_asset_path(asset_path)
            self.module_tags.append(module_tag_id)

    def _p_module_scalar(self, data):
        module_scalar_data = asset_path_to_data(data["ObjectPath"])
        self.module_scalars = self._p_scalars(module_scalar_data)
        

    def _p_ability_scalars(self, data):
        self.abilities_scalars = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            ability_scalar_data = asset_path_to_data(asset_path)
            self.abilities_scalars.append(self._p_scalars(ability_scalar_data))

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
        
        levels_data = data["Properties"]["LevelsData"]

        # Determine which stats are constants and which are not
        first_level_data = levels_data[0]
        non_constants = dict() # {non_constant_key: True}
        for level in levels_data[1:]: # iterate levels starting from i=1
            for key, value in level.items():
                if key in first_level_data and first_level_data[key] != value:
                    non_constants[key] = True

        if "ID" in non_constants:
            raise Exception(f"Data structure change: {self.__class__.__name__} {self.id} module scalar data has more than 1 BP ID specified in LevelData")
                
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

        module_scalars = dict()
        module_scalars["variables"] = parsed_levels_variable_stats
        module_scalars["constants"] = parsed_constant_stats

        return module_scalars
            

    def _p_title(self, data):
        self.name = parse_localization(data)

    def _p_description(self, data):
        self.description = parse_localization(data)

    def _p_text_tags(self, data):
        self.text_tags = []
        for elem in data:
            tag_localization = parse_localization(elem)
            self.text_tags.append(tag_localization)

    def _p_faction(self, data):
        asset_path = data["ObjectPath"]

        self.faction_id = Faction.get_from_asset_path(asset_path, log_tabs=1)

    def _p_module_classes(self, data):
        self.module_classes_ids = []
        for elem in data:
            asset_path = elem["ObjectPath"]
            module_class_id = ModuleClass.get_from_asset_path(asset_path)
            
            self.module_classes_ids.append(module_class_id)

    def _p_module_stats_table(self, data):
        asset_path = data["ObjectPath"]
        pass      

    def _p_module_type(self, data):
        asset_path = data["ObjectPath"]

        self.module_type_id = ModuleType.get_from_asset_path(asset_path, log_tabs=1)

    def _p_sockets(self, data):
        self.module_socket_type_ids = []
        for elem in data:
            asset_path = elem["Type"]["ObjectPath"]
            module_socket_type_id = ModuleSocketType.get_from_asset_path(asset_path)
            self.module_socket_type_ids.append(module_socket_type_id)

    def _p_levels(self, data):
        pass


def parse_modules():
    modules_source_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Mechanics\Meta\Entities\Modules")
    for file in os.listdir(modules_source_path):
        if file.endswith(".json"):
            full_path = os.path.join(modules_source_path, file)
            module_id = path_to_id(file)
            log(f"Parsing {Module.__name__} {module_id} from {full_path}", tabs=0)
            module_data = get_json_data(full_path)
            module = Module(module_id, module_data)

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

if __name__ == "__main__":
    parse_modules()