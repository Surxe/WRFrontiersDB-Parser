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
            "StatName": (parse_localization, "stat_name"),
            "MoreIsBetter": ("value", "more_is_better"),
            "UnitName": None,
            "UnitPattern": None,
            "UnitBaseline": ("value", "unit_baseline"),
            "UnitScaler": ("value", "unit_scaler"),
            "UnitExponent": ("value", "unit_exponent"),
            "ParamKey": None,
            "NumFractionDigits": ("value", "decimal_places"),
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)