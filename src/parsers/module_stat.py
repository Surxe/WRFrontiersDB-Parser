# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from utils import parse_localization, log

class ModuleStat(Object):
    objects = dict()  # Dictionary to hold all ModuleStat instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "StatName": self._p_stat_name,
            "MoreIsBetter": self._p_more_is_better,
            "UnitName": None,
            "UnitPattern": None,
            "UnitScaler": self._p_unit_scaler,
            "UnitExponent": self._p_unit_exponent,
            "ParamKey": None,
            "NumFractionDigits": self._p_num_fraction_digits,
        }

        for key, data in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function:
                    function(data)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'", tabs=2)

    def _p_stat_name(self, data):
        self.stat_name = parse_localization(data)

    def _p_more_is_better(self, data):
        self.more_is_better = data

    def _p_unit_scaler(self, data):
        self.unit_scalar = data

    def _p_unit_exponent(self, data):
        self.unit_exponent = data

    def _p_num_fraction_digits(self, data):
        self.decimal_places = data