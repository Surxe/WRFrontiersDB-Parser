# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.localization_table import parse_localization

from utils import asset_path_to_data, parse_colon_colon

class HonorReward(Object):
    objects = dict()  # Dictionary to hold all HonorReward instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "DescriptionCombat": (parse_localization, "description"),
            "Name": parse_localization,
            "RewardProcessor": (self._p_reward_processor, "condition"),
            "RewardTrigger": (self._p_reward_processor, "condition"),
            "HonorPoints": "value",
            "bIncremental": "value",
            "ProcessingTime": parse_colon_colon,
            "TitanCharge": "value",
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props)


    def _p_reward_processor(self, data):
        data = asset_path_to_data(data["ObjectPath"])
        if "Properties" in data:
            return data["Properties"]#["PlayerStateProperty"]