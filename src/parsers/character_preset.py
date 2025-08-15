# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.module import Module
from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path
from parsers.pilot import Pilot

from utils import asset_path_to_data, parse_colon_colon

class CharacterPreset(Object):
    objects = dict()  # Dictionary to hold all CharacterPreset instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": parse_localization,
            "TemplateType": self._p_template_type,
            "CharacterTypeAsset": self._p_character_type_asset,
            "CharacterType": self._p_character_type,
            "Modules": self._p_modules,
            "Pilot": self._p_pilot,
            "Icon": parse_image_asset_path,
            "RobotAIDataAsset": self._p_robot_ai_data_asset,
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_template_type(self, data):
        pass

    def _p_character_type_asset(self, data):
        pass

    def _p_character_type(self, data):
        pass

    def _p_modules(self, data):
        modules = []
        for entry in data:
            module = dict()
            module["id"] = Module.get_from_asset_path(entry["Module"]["ObjectPath"], sub_index=False)
            module["level"] = entry["Level"]
            modules.append(module)
        return modules

    def _p_pilot(self, data):
        pilot = dict()
        pilot["id"] = Pilot.get_from_asset_path(data["PilotAsset"]["ObjectPath"], sub_index=False)
        pilot["level"] = data["Level"] if "Level" in data else 1
        return pilot

    def _p_robot_ai_data_asset(self, data):
        pass
