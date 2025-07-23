# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.localization_table import parse_localization
from parsers.group_reward import GroupReward

class CustomizationType(Object):
    objects = dict()  # Dictionary to hold all CustomizationType instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"), 
            "GroupReward": (self._p_group_reward, "group_reward_id"),
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_group_reward(self, data):
        return GroupReward.get_from_asset_path(data["ObjectPath"])