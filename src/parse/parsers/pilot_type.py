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

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_rarity_data_asset(self, data):
        asset_path = data["ObjectPath"]
        return Rarity.get_from_asset_path(asset_path)

    def _p_group_reward(self, data):
        asset_path = data["ObjectPath"]
        return GroupReward.get_from_asset_path(asset_path)