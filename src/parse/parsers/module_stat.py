# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.localization_table import parse_localization
from loguru import logger

class ModuleStat(ParseObject):
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
            "MaxStatValueUI": "value",
            "MaxStatTitanValueUI": "value",
        }

        self._process_key_to_parser_function(key_to_parser_function, props)
    
    def format_value(self, value):
        """Raw stat value is converted to the value that would be displayed in game."""
        unit_baseline = getattr(self, "unit_baseline", 0.0)
        unit_scaler = getattr(self, "unit_scaler", 1.0)
        unit_exponent = getattr(self, "unit_exponent", 1.0)
        if unit_exponent < 0 and getattr(self, "more_is_better", None) is not None:
            logger.warning(f"Warning: ModuleStat {self.id} requires inversion but also has 'more_is_better' set to {self.more_is_better}, which may lead to confusing UX. Should it be double inverted?")
        if unit_exponent != 1.0 and unit_scaler != 1.0:
            logger.warning(f"New ModuleStat has both unit_exponent and unit_scaler. Please confirm the formula below is correct for these.")
        if unit_baseline not in [0.0, 1.0]:
            logger.warning(f"ModuleStat {self.id} has a non-standard baseline {unit_baseline}. Confirm the formula below is correct.")
        return ((value - unit_baseline) * unit_scaler) ** unit_exponent
    
    def get_ui_value_format_indicator(self) -> str:
        """
        Returns a string indicator for formatting UI values based on decimal places.
        
        Returns:
            str:
                x - Value is multiplicatively increased: base * (1+increase)
                / - Value is divisively decreased: base / (1+increase)
                Cx - Complement of value is multiplicatively increased: 1 - (1-base) * (1+increase)
        """
        unit_baseline = getattr(self, "unit_baseline", 0)
        unit_exponent = getattr(self, "unit_exponent", 1.0)
        if unit_exponent < 0 and getattr(self, "more_is_better", None) is not None:
            logger.warning(f"ModuleStat {self.id} requires inversion but also has 'more_is_better' set to {self.more_is_better}. Should it be double inverted? Setup handling.")
        
        if unit_exponent < 0:
            if unit_baseline != 0:
                logger.warning(f"New ModuleStat {self.id} has negative exponent {unit_exponent} and non-zero baseline {unit_baseline}. Confirm guessed handling is accurate.")
                return 'C/'
            else:
                return '/'
        elif unit_exponent > 0:
            if unit_baseline == 0.0:
                return 'x'
            elif unit_baseline == 1.0:
                return 'Cx'
            else:
                logger.warning(f"ModuleStat {self.id} has positive exponent {unit_exponent} and baseline {unit_baseline}. Setup handling.")
        logger.warning(f"ModuleStat {self.id} has unhandled combination of exponent {unit_exponent} and baseline {unit_baseline}. Defaulting to ''.")
        return ''
        
        