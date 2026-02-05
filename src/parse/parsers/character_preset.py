# Add two levels of parent dirs to sys path
import sys
import os

from loguru import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_json_data, OPTIONS, parse_colon_colon

from parsers.object import ParseObject
from parsers.image import Image, parse_image_asset_path
from parsers.pilot import Pilot
from parsers.module import Module
from parsers.localization_table import parse_localization
from utils import asset_path_to_data, asset_to_data

class CharacterPreset(ParseObject):
    objects = dict()

    def _parse(self):
        props = self.source_data["Properties"]
        
        key_to_parser_function = {
            "Icon": parse_image_asset_path,
            "Name": parse_localization,
            "bShowInProgressDiscover": None, #can't figure out its use, as TitanPro lvl13 presets have this as true
            "RobotAIDataAsset": None, #voiceline
            "TemplateType": None,
            "CharacterTypeAsset": None,
            "CharacterType": parse_colon_colon,
            "Modules": self._p_modules,
            "Pilot": (self._p_pilot, "pilot_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

        # Default is_factory_preset to False
        if not hasattr(self, "is_factory_preset"):
            self.is_factory_preset = False

        # Default character_type to Mech
        if not hasattr(self, "character_type"):
            self.character_type = "Mech"

    def _p_modules(self, data):
        modules = {}
        for index, module_entry in enumerate(data):
            module_id = Module.create_from_asset(module_entry["Module"], sub_index=False).to_ref()
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
        pilot = Pilot.create_from_asset(data["PilotAsset"]).to_ref()
        return pilot
    
    def set_is_factory_preset(self, is_factory_preset):
        self.is_factory_preset = is_factory_preset

def parse_factory_presets(to_file=False):
    root_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path)
    props = root_data[0]["Properties"]
    
    if 'DefaultPresets' in props:
        character_presets_data = asset_to_data(props["DefaultPresets"])
    elif 'InitialPlayerRobots' in props:#older structure
        character_presets_data = asset_to_data(props["InitialPlayerRobots"]) 
    else:
        logger.error("No default presets found in DA_Meta_Root data.")
        return
    props = character_presets_data["Properties"]

    def make_bot_preset(bot_preset_asset):
        bot_preset = CharacterPreset.create_from_asset(bot_preset_asset)
        bot_preset.set_is_factory_preset(True)
    
    if 'Presets' in props: #newer structure
        presets = props["Presets"]
        for bot_preset_entry in presets:
            make_bot_preset(bot_preset_entry)
            
    elif 'Robots' in props: #older structure
        robots = props["Robots"]
        for robot in robots:
            unlock_asset = robot["UnlockAsset"]
            if unlock_asset is not None:
                continue # only include presets that are available from the start
            make_bot_preset(robot["PresetAsset"])

    else:
        logger.error("No presets found in factory presets data.")
        return

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        CharacterPreset.to_file()
        Module.to_file()
        Pilot.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_factory_presets(to_file=True)