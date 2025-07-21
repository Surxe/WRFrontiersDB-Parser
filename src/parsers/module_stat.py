# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.localization_table import parse_localization

class ModuleStat(Object):
    objects = dict()  # Dictionary to hold all ModuleStat instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "StatName": parse_localization,
            "MoreIsBetter": "value",
            "UnitName": parse_localization,
            "UnitPattern": parse_localization,
            "UnitBaseline": "value",
            "UnitScaler": "value",
            "UnitExponent": "value",
            "ParamKey": ("value", "short_key"),
            "NumFractionDigits": ("value", "decimal_places"),
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)