# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from utils import parse_colon_colon
from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization

class Ability(Object):
    objects = dict()  # Dictionary to hold all Class instances

    def _parse(self):
        props = self.source_data.get("Properties")
        if not props:
            return
        
        key_to_parser_function = {
            "UberGraphFrame": None,
            "ConfirmationAction": (self._p_confirmation_action, "targeting"), #TODO
            "SPawnAction": None, #typo on their end
            "ProjectileTypes": (self._p_projectile_types, "TODO"), #TODO
            "AIConditions": None, #doesnt seem parseable, but AI bots use this
            "Name": parse_localization,
            "Description": parse_localization,
            "EffectType": parse_colon_colon,
            "bDeactivateIfOwnerDie": ("value", "deactivate_if_owner_die"),
            "Icon": (parse_image_asset_path, "icon_path"),
            "ActivationSoundEvent": None,
            "DeactivationSoundEvent": None,
            "CooldownChannel": None,
            "CooldownSpeedChannel": None,
            "GenericAbilityChannel": None,
            "PrimaryParameterChannel": None,
            "SecondaryParameterChannel": None,
            "InitialDurationChannel": None,
            "StatusFXManager": None,
            "bHasIndefiniteDuration": ("value", "has_indefinite_duration"),
            "AbilityScaler": (self._p_ability_scalar, "TODO"), #TODO
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=3)

    def _p_confirmation_action(self, value, prop_name):
        # TODO: Implement the parsing logic for ConfirmationAction
        pass

    def _p_projectile_types(self, value, prop_name):
        # TODO: Implement the parsing logic for ProjectileTypes
        pass

    def _p_ability_scalar(self, value, prop_name):
        # TODO: Implement the parsing logic for AbilityScaler
        pass