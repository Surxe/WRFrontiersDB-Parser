# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object, ParseAction
from utils import asset_path_to_data, parse_colon_colon
from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization
from parsers.module_stat import ModuleStat

class Ability(Object):
    objects = dict()  # Dictionary to hold all Class instances

    def _parse(self):
        props = self.source_data.get("Properties")
        if not props:
            return
        
        key_to_parser_function = {
            "UberGraphFrame": None,
            "ConfirmationAction": {'parser': self._p_confirmation_action, 'action': ParseAction.DICT_ENTRY, 'target_dict_path': "targeting"}, #TODO
            "TargetingActionWithConfirmation": {'parser': self._p_confirmation_action, 'action': ParseAction.DICT_ENTRY, 'target_dict_path': "targeting"},
            "SPawnAction": None, #typo on their end
            "ProjectileTypes": (self._p_projectile_types, "TODO"), #TODO
            "AIConditions": None, #doesnt seem parseable, but AI bots use this
            "Name": parse_localization,
            "Description": parse_localization,
            "Cooldown": "value",
            "CooldownPolicy": parse_colon_colon,
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
            "InitialDuration": "value",
            "PrimaryStatMetaInformation": (self._p_stat, "primary_stat_id"),
            "SecondaryStatMetaInformation": (self._p_stat, "secondary_stat_id"),
            "bHasIndefiniteDuration": ("value", "has_indefinite_duration"),
            "AbilityScaler": (self._p_ability_scalar, "TODO"), #TODO
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=3)

    def _p_confirmation_action(self, data: dict):
        conf_ac_data = asset_path_to_data(data["ObjectPath"])
        targeting_action_data = asset_path_to_data(conf_ac_data["Properties"]["TargetingAction"]["ObjectPath"])

        key_to_parser_function = {
            "FirstLocationOffset": "value",
            "DistanceBetweenTargets": "value",
            "NumTargets": "value",
            "MaxTargetingDistance": "value",
            "bIgnoreTypeOfTeamAttitude": ("value", "ignore_type_of_team_attitude"),
            "TypeOfTeamAttitude": lambda list: [parse_colon_colon(item) for item in list], # think this means it can pass through actors that are allies
            "bCanBePlacedOnWalls": ("value", "can_be_placed_on_walls"),
            "bRotateByNormal": None, # cannot discern how this works / what it means. rotate by normal curve? rotate what? this is used by Grim Snare
            "TunnelTraceHeight": None, # cannot discern how this works
            "bLockOnActor": ("value", "lock_on_actor"),
            "AssistanceRadius": None, # cannot discern how this works
            "ConeRadius": "value",
            "ConeHalfAngleInDegrees": "value",
            "MaxTargetNum": "value",
            "TargetingMarkerAction": None,
            "TargetingStartedSoundEvent": None,
            "TargetingEndedSoundEvent": None,
        }

        parsed_targeting_data = self._process_key_to_parser_function(
            key_to_parser_function, targeting_action_data["Properties"], log_descriptor="ConfirmationAction", tabs=4, set_attrs=False
        )

        return parsed_targeting_data

    def _p_projectile_types(self, data: dict):
        # TODO: Implement the parsing logic for ProjectileTypes
        pass

    def _p_ability_scalar(self, data: dict):
        # TODO: Implement the parsing logic for AbilityScaler
        pass

    def _p_stat(self, data: dict):
        stat_id = ModuleStat.get_from_asset_path(data["ObjectPath"])
        return stat_id