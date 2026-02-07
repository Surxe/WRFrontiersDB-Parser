# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

from parsers.localization_table import parse_localization
from parsers.group_reward import GroupReward

class CustomizationType(ParseObject):
    objects = dict()  # Dictionary to hold all CustomizationType instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "HumanName": (parse_localization, "name"), 
            "TypeTip": (parse_localization, "type_tip"),
            "GroupReward": (self._p_group_reward, "group_reward_ref"),
            "InfoPanelWidgetClass": None, #UI; old
            "ItemPictureWidgetClass": None, #UI; old
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_group_reward(self, data):
        return GroupReward.create_from_asset(data).to_ref()