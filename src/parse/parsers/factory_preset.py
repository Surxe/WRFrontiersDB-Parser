# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, get_json_data, OPTIONS

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
            "TemplateType": None,
            "CharacterTypeAsset": None,
            "Modules": (self._p_modules, "modules_ids"),
            "Pilot": (self._p_pilot, "pilot_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_modules(self, data):
        ids = []
        for module_entry in data:
            module = Module.get_from_asset_path(module_entry["Module"]["ObjectPath"], sub_index=False)
            ids.append(module)
        return ids

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