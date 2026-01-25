# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

from utils import ParseTarget, parse_colon_colon, asset_to_data

class MovementType(ParseObject):
    objects = dict()  # Dictionary to hold all GroupReward instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "MaxMobility": "value",
            "ChassisType": parse_colon_colon,
            "Flying_Z_Friction": "value",
            "MovementProperties": self._p_movement_properties,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="MovementType")
    
    def _p_movement_properties(self, list):
        parsed_props = []
        for entry in list:
            props = asset_to_data(entry)["Properties"]
            parsed_props.append(props)
        return parsed_props