# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object, ParseAction, ParseTarget
from utils import asset_path_to_data, log, parse_colon_colon
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
            "ExplodeCount": "value",
            "ImpactPointsCount": "value",
            "ThinBeamTime": "value",
            "ThickBeamTime": "value",
            "Damage": "value",
            "ActorMeshFXClass": None,
            "ActorClass": self._p_actor_class,
            "bStandaloneActor": ("value", "StandaloneActor"),
            "DestroyWithOwner": "value",
            "TargetingType": parse_colon_colon,
            "TargetingStartedSoundEvent": None,
            "TargetingEndedSoundEvent": None,
            #"TargetingMarkerClass": {'parser': self._p_confirmation_action, 'target': 'targeting'},
            "Struct Ref": None, # values in this dict are nonsense, but the keys are what I'd expect to be important, though should be referenced elsewhere with actual values. steel feathers dmg
            "SocketName": None,
            "SystemTemplate": None,
            "ReactionOnRecharge": None, #voice line
            "SpawnActorAction": (self._p_spawn_action, "spawn_action"),
            "ConfirmationAction": {'parser': self._p_confirmation_action, 'target': 'targeting'},
            "TargetingActionWithConfirmation": {'parser': self._p_confirmation_action, 'target': 'targeting'},
            "ImmediateTargetingAction": None,
            "SPawnAction": None, #typo on their end
            "ProjectileTypes": (self._p_projectile_types, "projectile_types"),
            "AIConditionOperator": parse_colon_colon,
            "AIConditions": self._p_ai_conditions, # TODO
            "Name": parse_localization,
            "Description": parse_localization,
            "PrimaryParameter": "value",
            "SecondaryParameter": "value",
            "Cooldown": "value",
            "CooldownPolicy": parse_colon_colon,
            "CastDuration": "value",
            "BattleHUDWidgetClass": None, #is a generic widget class, looks like nothing useful
            "EffectType": parse_colon_colon,
            "bDeactivateIfOwnerDie": ("value", "DeactivateIfOwnerDie"),
            "Icon": (parse_image_asset_path, "icon_path"),
            "CameraFX": None,
            "DurationParamName": None, #no clue but its "None", only used by steel feathers
            "ActivationReaction": None, #voiceline, like ActivationSoundEvent, maybe for "victim" though? used by tyr heal drone
            "CastStartedSoundEvent": None,
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
            "AttachSocketName": None,
            "ActiveStateBuffs": self._p_actor_class,
            "PrimaryStatMetaInformation": (self._p_stat, "primary_stat_id"),
            "SecondaryStatMetaInformation": (self._p_stat, "secondary_stat_id"),
            "bHasIndefiniteDuration": ("value", "HasIndefiniteDuration"),
            "AbilityScaler": (self._p_ability_scalar, "TODO"), #TODO
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=3)

    def _p_spawn_action(self, data: dict):
        spawn_action_data = asset_path_to_data(data["ObjectPath"])

        key_to_parser_function = {
            "TimeBetweenLaunch": "value",
            "FlyTime": "value",
            "FxLaunchLocation": None,
            "FxLaunchRotation": None,
            "LaunchFX": None,
            "LaunchAkEvent": None,
            "bDestroyActorOnExit": "value",
            "ActorClass": None,
            "bAttachedActor": None,
            "AttachSocketName": None,
        }

        parsed_spawn_data = self._process_key_to_parser_function(
            key_to_parser_function, spawn_action_data["Properties"], log_descriptor="SpawnAction", tabs=4, set_attrs=False, default_configuration={
                'target': ParseTarget.MATCH_KEY
            }
        )

        return parsed_spawn_data

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
        # Validate structure
        if len(data) != 1:
            last_socket_name = None
            for projectile_type in data:
                socket_name = projectile_type["SpawnSocketName"]
                if last_socket_name is not None and socket_name != "None" and socket_name == last_socket_name:
                    log(f"Data structure change: Multiple projectile types with the same socket names found: {last_socket_name} and {socket_name}.")
                last_socket_name = socket_name

        parsed_projectile_types = []
        for projectile_type in data:
            projectile_class_data = asset_path_to_data(projectile_type["ProjectileClass"]["ObjectPath"])
            props = asset_path_to_data(projectile_class_data["ClassDefaultObject"]["ObjectPath"])["Properties"]

            key_to_parser_function = {
                "UberGraphFrame": None,
                "ColorIdParam": None,
                "DelayTime": "value",
                "SocketNames": None,
                "RocketExplosionDebuffClass": self._p_actor_class,
                "ActorClass": self._p_actor_class,
                "AttachSocketName": None,
                "ActiveStateBuffs": self._p_actor_class,
                "AxisSocketName": None,
                "BuffActorClass": self._p_actor_class,
                "CollisionComponent": None,
                "MovementComponent": self._p_movement_component,
                "BuffsOnHit": self._p_actor_class,
                "DirectDamage": "value",
                "AoeDamage": "value",
                "VisualDamage": None,
                "ExplosionSettings": None, #doesn't mention radius, looks too niche/complex to bother with
                "OnComponentExploded": None, #references the same props, oddly
                "CorpseTime": "value",
                "CorpseVisible": "value", #unsure what this and corpse time refer to. This is used only by napalm, so I would have guessed its napalm area duration, but there's a buff for the napalm area that is 5s which is what I feel like it is in game. CorpseTime is 3s here. worth checking in game if its 3s or 5s #TODO
                "CollisionProfileName": "value",
                "ExpansionDistanceSettingsDefault": "value",
                "EffectiveDistanceSettingsDefault": "value",
                "MaxDistanceSettingsDefault": "value",
                "DeathDistanceSettingsDefault": "value",
                "OwnerReactionOnHit": None, # voiceline
                "VictimReactionOnHoming": None,
                "VictimReactionOnHit": None, # voiceline
                "MeshComponent": None,
                "GravityChangeFromDistance": "value",
                "NumberOfMulticomponent": None,
                "TitanChargePerHit": "value",
                "TracerFX": None,
                "AliveComponentsMaskParam": None,
                "CoordsParam": None,
                "DirectionParam": None,
                "InitialLifeSpan": None, # this is 0s for napalm ability, so can't be correct i think
                "WhizBySettings": None,
                "bAlwaysRelevant": None, #no clue what this means
                "InitialLifeSpan": "value",
                "CanBeTransfused": ("value", "CanBeTransferred"), # fairly positive this is referring to loki decoy transferring statuses
                "RootComponent": None,
            }

            parsed_proj = self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="ProjectileType", tabs=4, set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
            parsed_proj["SpawnSocketName"] = projectile_type["SpawnSocketName"]
            parsed_projectile_types.append(parsed_proj)

        return parsed_projectile_types
    
    def _p_actor_class(self, data: dict):
        if type(data) is list:
            for elem in data:
                return self._p_actor_class(elem)
        elif type(data) is dict:
            data = asset_path_to_data(data["ObjectPath"])
            data = asset_path_to_data(data["ClassDefaultObject"]["ObjectPath"])
            if 'Properties' not in data:
                return None
            
            key_to_parser_function = {
                "UberGraphFrame": None,
                "ReloadTimeFactor": "value",
                "Modifiers": "value",
                "MeshFX": None,
                "SocketToFX": None,
                "MeshFXClass": None,
                "StatusFXManager": None,
                "Lifetime": "value",
                "InitialLifetime": "value",
                "Icon": (parse_image_asset_path, "icon_path"),
                "ActiveSoundEventStart": None,
                "ActiveSoundEventFinish": None,
                "StatusFXManager": None,
                "ServerAttachedTime": None,
                "StackMode": parse_colon_colon,
                "AttachPoint": None,
                "BuffId": None,
                "DurationFX": None,
                "MeshFXFadeOutTime": None,
                "ProxyMeshFXClass": None,
                "ProxyMeshFXFadeOutTime": None,
                "CameraFX": None,
                "DirectDamage": "value",
                "AoeDamage": "value",
                "DirectDamagePerSecond": "value",
                "AoeDamagePerSecond": "value",
                "TickInterval": "value",
                "DamageExplosionSettings": None, #FX
            }

            parsed_data = self._process_key_to_parser_function(
                key_to_parser_function, data["Properties"], log_descriptor="ActorClass", tabs=5, set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                }
            )

            return parsed_data
    
    def _p_movement_component(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return None
        return data["Properties"]
    
    def _p_ai_conditions(self, data: dict):
        parsed_conditions = []
        for elem in data:
            if elem is None:
                continue
            condition_data = asset_path_to_data(elem["ObjectPath"])
            if 'Properties' not in condition_data:
                continue
            parsed_conditions.append(condition_data["Properties"])
        return parsed_conditions

    def _p_ability_scalar(self, data: dict):
        # TODO: Implement the parsing logic for AbilityScaler
        pass

    def _p_stat(self, data: dict):
        stat_id = ModuleStat.get_from_asset_path(data["ObjectPath"])
        return stat_id