# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.module_category import ModuleCategory
from parsers.module_socket_type import ModuleSocketType
from utils import parse_localization, log

class ModuleType(Object):
    objects = dict()  # Dictionary to hold all ModuleType instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Category": self._p_module_category,
            "HumanName": self._p_human_name,
            "Description": self._p_description,
            "BlueprintName": self._p_blueprint_name,
            "TagColor": self._p_tag_color,
            "TagBackgroundColor": self._p_tag_background_color,
            "ModuleSocketTypes": self._p_module_socket_types,
            "CharacterType": self._p_character_type,
            "ID": None,
        }

        for key, data in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function:
                    function(data)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'", tabs=2)

    def _p_module_category(self, data):
        asset_path = data["ObjectPath"]

        self.module_category_id = ModuleCategory.get_from_asset_path(asset_path)

    def _p_human_name(self, data):
        self.name = parse_localization(data)

    def _p_description(self, data):
        self.description = parse_localization(data)

    def _p_blueprint_name(self, data):
        self.blueprint_name = parse_localization(data)

    def _p_tag_color(self, data):
        self.tag_color = data["Hex"]

    def _p_tag_background_color(self, data):
        self.tag_background_color = data["Hex"]

    def _p_module_socket_types(self, data):
        module_socket_types_ids = []
        for socket_type in data:
            asset_path = socket_type["ObjectPath"]
            module_socket_types_ids.append(ModuleSocketType.get_from_asset_path(asset_path))

    def _p_character_type(self, data):
        self.character_type = data.split('ESCharacterType::')[-1]  # ESCharacterType::Titan -> Titan