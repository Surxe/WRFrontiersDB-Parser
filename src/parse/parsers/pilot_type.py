# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

from parsers.localization_table import parse_localization
from parsers.rarity import Rarity
from parsers.group_reward import GroupReward

class PilotType(ParseObject):
    objects = dict()  # Dictionary to hold all PilotType instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "RarityDataAsset": (self._p_rarity_data_asset, "rarity_id"),
            "ItemTypeName": (parse_localization, "name"),
            "GroupReward": (self._p_group_reward, "group_reward_id"),
            "PictureWidgetClass": None,
            "SortOrder": "value",
            "HasExtendedBio": "value",
            "CanChangeTalents": "value",
            "ItemInfoPanelClass": None, #UI; old
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _p_rarity_data_asset(self, data):
        return Rarity.create_from_asset(data).to_ref()

    def _p_group_reward(self, data):
        return GroupReward.create_from_asset(data).to_ref()