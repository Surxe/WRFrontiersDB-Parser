# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from parsers.localization_table import parse_localization

class GroupReward(Object):
    objects = dict()  # Dictionary to hold all GroupReward instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": parse_localization,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)