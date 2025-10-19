# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_json_data, OPTIONS, parse_colon_colon

from parsers.object import ParseObject
from parsers.image import Image, parse_image_asset_path
from parsers.pilot import Pilot
from parsers.module import Module
from parsers.localization_table import parse_localization
from utils import asset_path_to_data

class FactoryPreset(ParseObject):
    objects = dict()

    def _parse(self):
        props = self.source_data["Properties"]
        
        key_to_parser_function = {
            "Icon": parse_image_asset_path,
            "Name": parse_localization,
            "bShowInProgressDiscover": ("value", "production_status"),
            "RobotAIDataAsset": None, #voiceline
            "TemplateType": None,
            "CharacterTypeAsset": None,
            "CharacterType": parse_colon_colon,
            "Modules": self._p_modules,
            "Pilot": (self._p_pilot, "pilot_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

        # Default character_type to Mech
        if not hasattr(self, "character_type"):
            self.character_type = "Mech"

    def _p_modules(self, data):
        modules = {}
        for index, module_entry in enumerate(data):
            module_id = Module.get_from_asset_path(module_entry["Module"]["ObjectPath"], sub_index=False)
            socket_name = module_entry["ParentSocket"]
            parent_socket_index = module_entry["ParentModuleIndex"]
            # determine parent_socket_name by using the parent_socket_index lookup in modules
            if parent_socket_index == -1:
                parent_socket_name = None
            else:
                parent_socket_name = list(modules.keys())[parent_socket_index]
            modules[socket_name] = {
                "id": module_id,
                "parent_socket_name": parent_socket_name,
                "level": module_entry["Level"]
            }


        return modules
    def _p_pilot(self, data):
        pilot = Pilot.get_from_asset_path(data["PilotAsset"]["ObjectPath"])
        return pilot

def parse_factory_presets(to_file=False):
    root_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path)
    props = root_data[0]["Properties"]
    
    factory_presets_data = asset_path_to_data(props["DefaultPresets"]["ObjectPath"])
    
    for bot_preset_entry in factory_presets_data["Properties"]["Presets"]:
        bot_preset_asset_path = bot_preset_entry["ObjectPath"]
        bot_preset_id = FactoryPreset.get_from_asset_path(bot_preset_asset_path)
    

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        FactoryPreset.to_file()
        Module.to_file()
        Pilot.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_factory_presets(to_file=True)