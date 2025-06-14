# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, path_to_id, get_json_data, pascal_to_snake_case, asset_path_to_data, asset_path_to_file_path

from parsers.object import Object
from parsers.module_rarity import ModuleRarity
from parsers.rarity import Rarity

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
                "InventoryIcon": self._p_inventory_icon,
                "ModuleRarity": self._p_module_rarity,
            }
            for key, parser_function in key_to_parser_function.items():
                if key in props:
                    value = parser_function(props[key])
                    setattr(self, pascal_to_snake_case(key), value)

    
    def _p_production_status(self, data):
        return data.split("ESCharacterModuleProductionStatus::")[-1] # "ESCharacterModuleProductionStatus::Ready" -> "Ready"
        
    def _p_inventory_icon(self, data):
        return path_to_id(data["AssetPathName"])
    
    def _p_module_rarity(self, data):
        asset_path = data["ObjectPath"]
        mr_id = path_to_id(asset_path)
        mr = ModuleRarity.get_from_id(mr_id)
        if mr is None:
            file_path = asset_path_to_file_path(asset_path)
            log(f"Parsing {ModuleRarity.__name__} {mr_id} from {file_path}", tabs=1)
            mr_data = get_json_data(file_path)[0]
            mr = ModuleRarity(mr_id, mr_data)
        return mr_id

def parse_modules():
    modules_source_path = os.path.join(os.getenv('EXPORTS_PATH'), r"WRFrontiers\Content\Sparrow\Mechanics\Meta\Entities\Modules")
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

if __name__ == "__main__":
    parse_modules()