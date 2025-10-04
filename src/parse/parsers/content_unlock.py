# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization
from parsers.group_reward import GroupReward

class ContentUnlock(Object):
    objects = dict()  # Dictionary to hold all ContentUnlock instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Slot": None, # not really necessary
            "UnlockType": parse_localization,
            "UnlockImage": (parse_image_asset_path, "image_path"),
            "Description": parse_localization,
            "TypeName": (parse_localization, "type_name"),
            "UnlockMesh": None, 
            "VisibleInUI": "value",
            "GroupReward": (lambda group_reward: GroupReward.get_from_asset_path(group_reward["ObjectPath"]), "group_reward_id"),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)