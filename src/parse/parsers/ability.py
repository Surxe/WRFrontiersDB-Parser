# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parse.parsers.module_tag import ModuleTag
from parsers.object import ParseObject
from utils import logger, ParseTarget, ParseAction, process_key_to_parser_function, asset_path_to_data, parse_colon_colon, parse_editor_curve_data, merge_dicts
from parsers.image import parse_image_asset_path
from parsers.localization_table import parse_localization
from parsers.module_stat import ModuleStat

class Ability(ParseObject):
    objects = dict()  # Dictionary to hold all Class instances

    def _parse(self):
        if 'ClassDefaultObject' in self.source_data:
            data = asset_path_to_data(self.source_data["ClassDefaultObject"]["ObjectPath"])
        else:
            data = self.source_data
        # Wrapper for main ability parsing
        overlayed_data = self._parse_from_data(data)
        for key, value in overlayed_data.items():
            setattr(self, key, value)

        # Locate WeaponInfos under the misc attribute and move it to the weapon_id attribute
        if hasattr(self, 'misc') and 'spawn_actor_action' in self.misc and 'ActorClass' in self.misc['spawn_actor_action'] and 'WeaponInfos' in self.misc['spawn_actor_action']['ActorClass']:
            self.weapon_id = self.misc['spawn_actor_action']['ActorClass'].pop('WeaponInfos')

    def _parse_from_data(self, source_data: dict):
        props = source_data.get("Properties")
        if not props:
            return {}

        template_ability_data = None
        if 'Template' in source_data:
            template_ability_data = self._parse_and_merge_template(source_data["Template"])

        key_to_parser_function = {
            "UberGraphFrame": None,
            "ExplodeCount": "value",
            "ImpactPointsCount": "value",
            "ThinBeamTime": "value",
            "ThickBeamTime": "value",
            "Damage": parse_editor_curve_data,
            "ActorMeshFXClass": None,
            "ActorClass": self._p_actor_class,
            "bStandaloneActor": "value",
            "DestroyWithOwner": "value",
            "TargetingType": {"parser": parse_colon_colon, "action": ParseAction.DICT_ENTRY, "target_dict_path": "targeting", "target": ParseTarget.MATCH_KEY},
            "TargetingStartedSoundEvent": None,
            "TargetingEndedSoundEvent": None,
            #"TargetingMarkerClass": {'parser': self._p_confirmation_action, 'target': 'targeting'},
            "Struct Ref": None, # values in this dict are nonsense, but the keys are what I'd expect to be important, though should be referenced elsewhere with actual values. steel feathers dmg
            "SocketName": None,
            "SystemTemplate": None,
            "ReactionOnRecharge": None, #voice line
            "SpawnActorAction": {"parser": self._p_spawn_action, "action": ParseAction.DICT_ENTRY, "target": ParseTarget.MATCH_KEY_SNAKE},
            "ConfirmationAction": {"parser": self._p_confirmation_action, "action": ParseAction.DICT_ENTRY, "target_dict_path": "targeting", "target": ParseTarget.MATCH_KEY},
            "HackingCastAction": None, #TODO kernel
            "ActorCDOShapeComponent": self._p_actor_class,
            "TargetingActionWithConfirmation": {"parser": self._p_confirmation_action, "action": ParseAction.DICT_ENTRY, "target_dict_path": "targeting", "target": ParseTarget.MATCH_KEY},
            "ImmediateTargetingAction": None,
            "SPawnAction": None, #typo on their end
            "ProjectileTypes": {"parser": self._p_projectile_types, "action": ParseAction.ATTRIBUTE, "target": ParseTarget.MATCH_KEY_SNAKE},
            "AIConditionOperator": {"parser": parse_colon_colon, "action": ParseAction.DICT_ENTRY, "target_dict_path": "ai", "target": "condition_operator"},
            "AIConditions": {"parser": self._p_ai_conditions, "action": ParseAction.DICT_ENTRY, "target_dict_path": "ai", "target": "conditions"},
            "ActivationChargePoints": "value",
            "Name": {"parser": parse_localization, "action": ParseAction.ATTRIBUTE, "target": ParseTarget.MATCH_KEY_SNAKE},
            "Description": {"parser": parse_localization, "action": ParseAction.ATTRIBUTE, "target": ParseTarget.MATCH_KEY_SNAKE},
            "PrimaryParameter": "value",
            "SecondaryParameter": "value",
            "Cooldown": {"parser": "value", "action": ParseAction.DICT_ENTRY, "target_dict_path": "cooldown", "target": ParseTarget.MATCH_KEY},
            "CooldownPolicy": {"parser": parse_colon_colon, "action": ParseAction.DICT_ENTRY, "target_dict_path": "cooldown", "target": ParseTarget.MATCH_KEY},
            "CastDuration": "value",
            "BattleHUDWidgetClass": None, #is a generic widget class, looks like nothing useful
            "EffectType": self._p_effect_type,
            "bDeactivateIfOwnerDie": "value",
            "Icon": {"parser": parse_image_asset_path, "action": ParseAction.ATTRIBUTE, "target": "icon_path"},
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
            "PrimaryStatMetaInformation": None, #already included in Module
            "SecondaryStatMetaInformation": None, #already included in Module. Supply Surge for example in ability file says primary is Duration, secondary is SpeedBoost. In DA module file, primary is Duration, secondary is *ActEfficiency(correct)*
            "bHasIndefiniteDuration": "value",
            "AbilityScaler": None, # interestingly, contains blank information. ability scalers are specified in the original module file
            "IsHidden": "value",
            "InitialCooldown": None, #often 0
            "bMovementAbility": None,
            "MaxCharges": None, # says blackout has 1 charge but it doesnt
            "RampUpDuration": "value",
            "ReactionToShooting": parse_colon_colon,
            "DeactivationReaction": None, #FX of swarm
            "DeactivationTargetSoundEvent": None,
            "DeactivationOtherSoundEvent": None,
            "ActivationOtherSoundEvent": None,
            "ActivationTargetSoundEvent": None,
            "TensionLinkBeamFX": None,
            "AuraFX": None,
            "TrailFX": None,
            "ColorIdParam": None,
            "WeaponFX": None,
            "StartCastAnimation": None,
            "CastMeshFX": None,
            "OvertipFX": None,
            "OvertipFXDestroyPolicy": None,
            "BeamDistanceRTPC": None,
            "StealthAfterFireRestoreTimeout": "value",
            "TeleportingSoundEvent": None,
            "EndOfLifetimeSoundEvent": None,
            "BeaconClass": None,
            "MeshFX": None,
            "TeleportFX": None,
            "StartCastFX": None,
            "DamageDecalClass": None,
            "FieldRadius": "value", # matriarch
            "CloneSpawnLocationOffset": "value",
            "AIControllerClass": None,
            "BotBuffClass": None,
            "CloneBuffClass": None,
            "CopyToCloneBuffs": None,
            "BotDeathFX": None,
            "BotDeathSoundEvent": None,
            "CancellationCooldown": "value",
            "StackingBuffClass": self._p_actor_class,
            "MaxStacks": "value",
            "MaxTargetingDistance": {"parser": "value", "action": ParseAction.DICT_ENTRY, "target_dict_path": "targeting", "target": ParseTarget.MATCH_KEY}, #lancelot, despite it not having any targeting and iirc radius specified elsewhere
            "Mobility Modifier": "value",  # grim snare
            "Max Speed Modifier": "value",  
            "PreferredInputAction": None, #cyclops targeting, too complex to bother
            "TransfusionRaySoundEvent": None,
            "Radius": "value",
            "TransfusionInterval": "value", #bullwark
            "TransfusionThreshold": "value", #bullwark, unknown meaning
            "TransfusionSourceFx": None,
            "TransfusionSphereFx": None,
            "TransfusionRayFx": None,
            "LaunchSoundEvent": None, #bulgasari
            "TimeBetweenLaunch": "value", #bulgasari
            "LaunchCount": "value", #bulgasari
            "DamageAreaDecalClass": None,
            "LaunchFX": None,
            "LaunchLocation": "value",
            "LaunchRotation": "value",
            "FlyTime": "value", #unknown usage for bulgasari
            "MaxSpawnDistance": "value",
            "bLockOnActor": {"parser": "value", "action": ParseAction.DICT_ENTRY, "target_dict_path": "targeting", "target": ParseTarget.MATCH_KEY},
            "TargetingMarkerClass": None,
            "AssistanceRadius": None,
            "RetributionAnimTime": None,
            "WeaponInfos": {"parser": self._p_weapon_infos, "action": ParseAction.ATTRIBUTE, "target": "weapon_id"}, # ares retribution and volta tesla coil
            "ActivateWeaponsAction": {"parser": self._p_activate_weapons_action, "action": ParseAction.ATTRIBUTE, "target": "weapon_id"},
            "TurnSpeed": None, #homign pack
            "CruiseHeightRange": None,
            "CruiseRollSeconds": None,
            "CruiseRollSeconds": None,
            "HomingClimbSpeed": None,
            "HomingClimbAcceleration": None,
            "HomingCruiseAcceleration": None,
            "HomingClimbTurnRate": None,
            "HomingCruiseTurnRate": None,
            "CruiseHeightMin": None,
            "RandomizeCruiseRoll": None, #homing pack end
            "AreaRadius": "value",
            "ActiveRadius": "value",
            "PrimaryTargetVFX": None,
            "SecondaryTargetVFX": None,
            "TargetHitSFX": None,
            "PrimaryTargetImpactVFX": None,
            "VoiceoverOnHit": None,
            "VoiceoverOnHit_Victim": None,
            "SpawnLocationOffset": "value",  # umbrella
            "bCheckMinSpawnHeight": None,
            "MinSpawnHeight": "value",  # umbrella
            "ActiveStatFX": None,
            "CastReaction": None, #voiceline
            "TrajectoryHint": None,
            "ActiveStateFX": None,
            "DeathSequencesContainer": None, #loki
            "bCanBeCanceledWhileActive": "value",
            "CastEndedSoundEvent": None,
            "IsCasting": "value", #indicates channel i would guess
            "Area Radius": "value",
            "BuffOnHit": self._p_actor_class,  # this is used by bulgasari, but the buff is not defined in the game files, so not sure what it does
            "ExplosionSettings": None, #impact vfx
            "DamageFactor": "value",
            "DamageRedirectSoundEvent": None,
            "DamageReceiveSoundEvent": None,
            "DamageRedirectVisuals": None,
            "ShieldVisuals": None,
            "bStartWithMaxCharges": "value", #false for counterattack, odd, its cycle gear, so none have charges
            "ChargeTrigger": self._p_charge_trigger,
            "Spread": "value",
            "LaunchHeight": "value",
            "SingulatorsCount": "value",
            "SpawnSocketNames": None, #matriarch singulators
            "SweepObjectTypes": None,
            "Swipe Impulse Magnitude": "value",  # grim scythe
            "On Collision Buff Duration": "value",
            "On Collision AoE Damage": parse_editor_curve_data,
            "SweepRadius": "value",
            "Explosion Impulse Magnitude": "value",
            "Explosion Radius": "value",
            "Teleport Trace System": None,
            "Explosion Vertical Angle": "value",
            "Swipe Vertical Angle": "value",
            "TeleportAction": None,
            "TeleportDistance": "value",
            "Actions": self._p_actions,
            "bAllowStatsReporting": "value", #i.e dash does not have stats reporting, defaulted to true
            "EndCastFX": None,
            "DamageBuff": self._p_actor_class, # gamma beam
            "TargetPosParam": None,
            "ShowRayParam": None,
            "FadeOutParam": None,
            "CharacterAttitudeRTPC": None,
            "DamageDistanceMin": "value", #does gamma beam really deal 0 dmg in 50m or less?
            "DamageDistanceMax": "value",
            "BuffOnEnemyClass": self._p_actor_class, # recon
            "MaxSpeedModifier": self._p_max_speed_modifier,
            "MaxAccelerationModifier": self._p_max_speed_modifier,
            "CollisionBoxExtent": "value",
            "ImpulsePower": "value",
            "VerticalImpulsePowerRatio": "value",
            "MinVerticalImpulsePower": "value",
            "DistanceBetweenMines": "value", #minefield
            "MineFieldCount": "value",
            "ActivationFuelCost": "value", #grim l shoulder
            "bUseOwnerCollisionProfile": "value",
            "CustomCollisionProfile": None,
            "TargetBuff": self._p_actor_class,  # fuel burn
            "JumpFuelCost": "value", #jump jet (flying)
            "FuelCostToStartAirborne": "value",
            "JumpTime": "value",
            "JumpPreparingSoundEvent": None,
            "JumpSoundEvent": None,
            "FlyStartedSoundEvent": None,
            "FlyFinishedSoundEvent": None,
            "JetpackMaxVerticalSpeed": "value",
            "bOverrideAirControl": "value",
            "AirControl": "value",
            "JetpackStartVerticalImpulse": "value",
            "JetpackJumpAccelerationForce": "value",
            "ResourceUnitsPerSecond": {"parser": "value", "action": ParseAction.DICT_ENTRY, "target_dict_path": "resource", "target": ParseTarget.MATCH_KEY_SNAKE}, #fuel reserve
            "ResourceType": {"parser": "value", "action": ParseAction.DICT_ENTRY, "target_dict_path": "resource", "target": ParseTarget.MATCH_KEY_SNAKE},
            "CameraShakeOnDamage": None, # flashbang
            "SpawnActorCollisionHandlingMethod": None, #varangian
            "Height": "value",
            "MaxRegeneratedUnits": "value", #fuel reserve
            "RestrictActivationWhileAirborne": "value",
            "WeaponNiagaraFX": None, #instant reload
            "UsageFuelCost": "value", #alpha chassis dash
            "FuelConsumptionDuration": "value",
            "MinimumDuration": "value",
            "LevitationHeight": "value", #anansi legs
            "AccelerationForce": "value",
            "MaxVelocityHorizontal": "value",
            "DragCoefficientX": "value",
            "DragCoefficientY": "value",
            "FuelUsagePerSecond": "value",
            "MinFuelRequired": "value",
            "SpawnRelativeLocation": "value", #old camo web
            "VerticalAccelerationForceCurve": self._p_vertical_accel_curve,
            "AirControlBoostMultiplier": "value",
            "AirControlBoostVelocityThreshold": "value",
            "JumpMovementMode": parse_colon_colon,
            "GroundAction": None, #anansi chassis, too complex to bother
            "InAirAction": None, #same
            "InAirJumpFuelCostPenaltyByNum": "value",
            "AfterJumpFuelRegenerationDelay": "value",
            "DelayBetweenActions": "value",
            "ActivationFuelCost": "value", #blink
            "TargetingAction": self._p_targeting_action,
            "FriendlyEffectMaterial": None,
            "HostileEffectMaterial": None,
            "TransitionTime": "value",
            "InputActionOccupationPriority": None, #orbital strike
            "CompensationPower": "value", #kumo chassis
            "BuffAreaDistance": "value", #kumo torso
            "DistanceRange": None, #TODO kernel
            "BuffOnTarget": None, #TODO kernel
        }

        my_ability_data = self._process_key_to_parser_function(
            key_to_parser_function, props, set_attrs=False, default_configuration={
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'misc',
                'target': ParseTarget.MATCH_KEY
            })

        overlayed_data = merge_dicts(template_ability_data, my_ability_data)

        return overlayed_data

    def _p_vertical_accel_curve(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])["Properties"]
        return parse_editor_curve_data(data)


    def _p_effect_type(self, data: str):
        etype = parse_colon_colon(data)
        # Return the effect type if it cant be casted to an int
        if not etype.isdigit():
            return etype
        #EffectType can be Defensive, Attack, or numerical code like 16
    
    def _p_activate_weapons_action(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if data is None or data == [] or 'Properties' not in data:
            return
        return self._p_weapon_infos(data["Properties"]["WeaponInfos"])

    def _p_spawn_action(self, data: dict):
        logger.debug(f"Parsing spawn action for {self.id}")

        spawn_action_data = asset_path_to_data(data["ObjectPath"])

        if 'Properties' not in spawn_action_data:
            return

        key_to_parser_function = {
            "TimeBetweenLaunch": "value",
            "FlyTime": "value",
            "FxLaunchLocation": None,
            "FxLaunchRotation": None,
            "LaunchFX": None,
            "LaunchAkEvent": None,
            "bDestroyActorOnExit": "value",
            "ActorClass": self._p_actor_class,
            "bAttachedActor": None,
            "AttachSocketName": None,
            "OnActorSpawning": None, #matriarch shoulder L
            "LaunchFXColorIdParam": None,
        }

        parsed_spawn_data = self._process_key_to_parser_function(
            key_to_parser_function, spawn_action_data["Properties"], log_descriptor="SpawnAction", set_attrs=False, default_configuration={
                'target': ParseTarget.MATCH_KEY
            }
        )

        return parsed_spawn_data
    
    def _p_targeting_action(self, data: dict):
        logger.debug(f"Parsing targeting action for {self.id}")
        targeting_action_data = asset_path_to_data(data["ObjectPath"])

        if data is None or data == [] or 'Properties' not in data:
            return

        key_to_parser_function = {
            "FirstLocationOffset": "value",
            "DistanceBetweenTargets": "value",
            "NumTargets": "value",
            "MaxTargetingDistance": "value",
            "bIgnoreTypeOfTeamAttitude": "value",
            "TypeOfTeamAttitude": lambda list: [parse_colon_colon(item) for item in list], # think this means it can pass through actors that are allies
            "bCanBePlacedOnWalls": "value",
            "bRotateByNormal": None, # cannot discern how this works / what it means. rotate by normal curve? rotate what? this is used by Grim Snare
            "TunnelTraceHeight": None, # cannot discern how this works
            "bLockOnActor": "value",
            "AssistanceRadius": None, # cannot discern how this works
            "ConeRadius": "value",
            "ConeHalfAngleInDegrees": "value",
            "MaxTargetNum": "value",
            "TargetingMarkerAction": None,
            "TargetingStartedSoundEvent": None,
            "TargetingEndedSoundEvent": None,
        }

        parsed_targeting_data = self._process_key_to_parser_function(
            key_to_parser_function, targeting_action_data["Properties"], log_descriptor="ConfirmationAction", set_attrs=False
        )

        return parsed_targeting_data

    def _p_confirmation_action(self, data: dict):
        logger.debug(f"Parsing confirmation action for {self.id}")

        conf_ac_data = asset_path_to_data(data["ObjectPath"])
        return self._p_targeting_action(conf_ac_data["Properties"]["TargetingAction"])

        

    def _p_projectile_types(self, data: dict):
        logger.debug(f"Parsing projectile types for {self.id}")

        # Validate structure
        if len(data) != 1:
            last_socket_name = None
            for projectile_type in data:
                socket_name = projectile_type["SpawnSocketName"]
                if last_socket_name is not None and socket_name != "None" and socket_name == last_socket_name:
                    logger.error(f"Data structure change: Multiple projectile types with the same socket names found: {last_socket_name} and {socket_name}.")
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
                "AoeDamage": parse_editor_curve_data,
                "VisualDamage": None,
                "ExplosionSettings": None, #doesn't mention radius, looks too niche/complex to bother with
                "OnComponentExploded": None, #references the same props, oddly
                "CorpseTime": "value",
                "CorpseVisible": "value", #unsure what this and corpse time refer to. This is used only by napalm, so I would have guessed its napalm area duration, but there's a buff for the napalm area that is 5s which is what I feel like it is in game. CorpseTime is 3s here. worth checking in game if its 3s or 5s #TODO
                "CollisionProfileName": "value",
                "ExpansionDistanceSettingsDefault": (self._p_distance, "ExpansionDistanceSettings"),
                "EffectiveDistanceSettingsDefault": (self._p_distance, "EffectiveDistanceSettings"),
                "MaxDistanceSettingsDefault": (self._p_distance, "MaxDistanceSettings"),
                "DeathDistanceSettingsDefault": (self._p_distance, "DeathDistanceSettings"),
                "DefaultDistanceSettings": (parse_editor_curve_data, "DefaultDistanceSettings"),
                "OwnerReactionOnHit": None, # voiceline
                "VictimReactionOnHoming": None,
                "VictimReactionOnHit": None, # voiceline
                "MeshComponent": None,
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
                "Stream": None,
                "DamgeZoneMultiplyer": "value", #blast wave
                "BlinkedEffect": None, #fx
                "FriendColor": None,
                "CurrentColor": None,
                "HostileColor": None,
                "StartOfDelaySoundEvent": None,
                "StopOfDelaySoundEvent": None,
                "PushingType": None, #also a numerical code
                "PushingSettings": self._p_pushing_settings,
                "bPassThroughShields": "value", #magnetic sensor
                "bCanBeDamaged": "value",
                "bSetVFXSizeFromCollision": None, #repulsor
                "ObstaclesCollisionComponent": None,
                "bUseGravityChangeFromDistanceCurve": "value", #ghost turret
                "GravityChangeFromDistance": parse_editor_curve_data,
                "ContinuousPushing": None, #kinetic pulse, is empty
                "PushingEffect": None, #NSI - vfx?
                "AvoidMarker": None,
                "ContinuousPushingSettings": self._p_cont_pushing_settings,
                "TracerOffsetTime": None,
            }

            parsed_proj = self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="ProjectileType", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
            parsed_proj["SpawnSocketName"] = projectile_type["SpawnSocketName"]
            parsed_projectile_types.append(parsed_proj)

        return parsed_projectile_types
    
    def _p_cont_pushing_settings(self, data: dict):
        key_to_parser_function = {
            "Interval": "value",
            "PushingSettings": self._p_pushing_settings,
        }
        return self._process_key_to_parser_function(
            key_to_parser_function, data, log_descriptor="ContinuousPushingSettings", set_attrs=False, default_configuration={
                'target': ParseTarget.MATCH_KEY
            }
        )
    
    def _p_actions(self, list: dict):
        parsed_actions = []
        for elem in list:
            data = asset_path_to_data(elem["ObjectPath"])
            if 'Properties' not in data:
                continue
            action_data = data["Properties"]
            
            key_to_parser_function = {
                "StartDelay": "value",
                "CanStartOnGround": "value",
                "CanStartMidair": "value",
                "bHasDuration": "value",
                "Duration": "value",
                "MaxSpeedModifier": self._p_max_speed_modifier,
                "bPlayVisualFX": None,
                "StartImpulse": "value",
                "bHasVelocityThreshold": "value",
                "VelocityThreshold": "value",
                "VerticalAcceleration": "value",
                "RequestedDirectionAcceleration": "value",
                "MinSpeedToStartAction": "value", #alpha chassis dash
                "bBlocksAirControl": "value",
            }

            parsed_action = self._process_key_to_parser_function(
                key_to_parser_function, action_data, log_descriptor="Action", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                }
            )

            parsed_actions.append(parsed_action)

        return parsed_actions

    def _p_max_speed_modifier(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if "Properties" not in data:
            return
        parsed_data = dict()
        if "Value" in data["Properties"]:
            parsed_data["Value"] = data["Properties"]["Value"]
        if "Type" in data["Properties"]:
            parsed_data["Type"] = parse_colon_colon(data["Properties"]["Type"])
        return parsed_data


    def _p_ai_condition(self, data: dict) -> dict:
        """Recursively parse and overlay AI condition and its template."""
        condition_data = asset_path_to_data(data["ObjectPath"])
        if not condition_data:
            return {}
        # Recursively parse template if present
        if "Template" in condition_data:
            base = self._p_ai_condition(condition_data["Template"])
        else:
            base = {}
        props = condition_data.get("Properties", {})
        result = dict(base)
        result.update(props)
        return result

    def _p_ai_conditions(self, data: dict):
        parsed_conditions = []
        for elem in data:
            if elem is None:
                continue
            parsed_ai_condition = self._p_ai_condition(elem)
            if parsed_ai_condition:
                parsed_conditions.append(parsed_ai_condition)
        if not parsed_conditions:
            return
        return parsed_conditions

    def _p_stat(self, data: dict):
        stat_id = ModuleStat.get_from_asset_path(data["ObjectPath"])
        return stat_id
    
    def _p_pushing_settings(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return
        else:
            return data["Properties"]
        
    def _p_charge_trigger(self, data: dict):
        if data is None or data == []:
            return
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return
        return data["Properties"]
    
    def _p_actor_class(self, data):
        return p_actor_class(data)
    
    def _p_movement_component(self, data):
        return p_movement_component(data)
    
    def _p_weapon_infos(self, data: dict):
        logger.debug(f"Parsing weapon infos for {self.id}")
        return p_weapon_infos(data)
    
    def _p_distance(self, data):
        return data["Distance"]

def p_armor_zones(list: list):
    armor_zone_names = []
    for elem in list:
        armor_zone_asset_path = elem["ObjectPath"]
        # armor zone file does not contain any front-facing information, so instead going to use the file name as a reference here
        armor_zone_name = armor_zone_asset_path.split("DA_ArmorZone_")[-1].split(".")[0] #../DA_ArmorZone_Torso.0 -> Torso
        armor_zone_names.append(armor_zone_name)
    return armor_zone_names

def p_modifiers(list: list):
    parsed_modifiers = []
    for modifier in list:
        what = parse_colon_colon(modifier["Key"])
        operator = parse_colon_colon(modifier["Value"]["ModifierType"])
        factor = modifier["Value"]["Factor"]
        parsed_modifier = {
            "what": what,
            "operator": operator,
            "value": factor
        }
        parsed_modifiers.append(parsed_modifier)
    return parsed_modifiers

def p_expansion_settings(data: dict):
    # #contains multiple float curves that utilize tangent curves. Unsure which curve is used. Harpy torso, gemini, quantum 
    # curves = asset_path_to_data(data["ExternalCurve"]["ObjectPath"])["FloatCurves"]
    # parsed_curves = []
    # for curve in curves:
    #     parsed_curve = parse_editor_curve_data(curve)
    #     if parsed_curve:
    #         parsed_curves.append(parsed_curve)
    # return parsed_curves

    return True # placeholder to indicate presence of expansion settings, which is enough for now

def p_expansion_template(data: dict):
    data = asset_path_to_data(data["ObjectPath"])
    if 'Properties' not in data:
        return
    props = data["Properties"]
    key_to_parser_function = {
        "FinishLength": "value",
        "Type": parse_colon_colon,
        "ExpansionDistance": "value",
        "bFactorGravityIntoExpansion": "value",
        "ExpansionSettings": p_expansion_settings, 
        "InitialRadius": "value",
        "FinishRadius": "value",
    }
    return process_key_to_parser_function(key_to_parser_function, props, log_descriptor="ExpansionTemplate", set_attrs=False, default_configuration={
        'target': ParseTarget.MATCH_KEY
    })

def p_movement_component(data: dict):
    data = asset_path_to_data(data["ObjectPath"])
    if 'Properties' not in data:
        return
    key_to_parser_function = {
        "InitialSpeed": "value",
        "ExpansionTemplate": p_expansion_template,
        "TurnSpeed": "value",
        "CruiseHeightMin": "value",
        "CruiseHeightRange": "value",
        "CruiseRollSeconds": "value",
        "CruiseHeightObstacleTestStep": "value",
        "HomingClimbSpeed": "value",
        "HomingCruiseSpeed": "value",
        "HomingAttackSpeed": "value",
        "HomingClimbAcceleration": "value",
        "HomingCruiseAcceleration": "value",
        "HomingAttackAcceleration": "value",
        "HomingClimbTurnRate": "value",
        "HomingCruiseTurnRate": "value",
        "HomingAttackTurnRate": "value",
        "InitialSpeed": "value",
        "ProjectileGravityScale": "value",
        "MaxSpeed": "value",
        "ProjectileGravityScale": "value",
        "DistanceToDisableVelocityPrediction": "value",
        "bSimplifiedMovementCalculation": "value",
        "bShouldBounce": "value",
        "Bounciness": "value",
        "Friction": "value",
        "PlaneConstraintNormal": "value",
        "LaunchSpeed": "value",
        "Velocity": "value",
        "bCruiseRoll": "value",
        "bIsHomingProjectile": "value",
        "bCruiseAvoidObstacles": "value",
        "bForceSubStepping": "value",
        "bCruiseAvoidObstacles": "value",
        "bEnableCruiseMode": "value",
    }
    return process_key_to_parser_function(key_to_parser_function, data["Properties"], log_descriptor="MovementComponent", set_attrs=False, default_configuration={
        'target': ParseTarget.MATCH_KEY
    })

def p_focus_component(data: dict):
    data = asset_path_to_data(data["ObjectPath"])
    if 'Properties' not in data:
        return
    return data["Properties"]

def p_damage_applier(data: dict):
    data = asset_path_to_data(data["ObjectPath"])["Properties"]

    key_to_parser_function = {
        "TickFunction": "value",
        "DirectDamagePerSecond": "value",
        "DamageStartedAudioEvent": None,
        "DamageStopedAudioEvent": None,
        "DamageMeshFXClass": None,
    }

    parsed_data = process_key_to_parser_function(
            key_to_parser_function, data, log_descriptor="ActorClass", set_attrs=False, default_configuration={
                'target': ParseTarget.MATCH_KEY
            }
        )

    return parsed_data

def p_weapon_infos(list: list):
    # Lazy import to avoid circular dependency
    from parsers.character_module import CharacterModule

    last_weapon_module_asset_path = None
    for weapon_info in list:
        weapon_module_asset_path = weapon_info["WeaponModule"]["ObjectPath"]
        # Ensure the path is not different to the previous one
        if last_weapon_module_asset_path is not None and weapon_module_asset_path != last_weapon_module_asset_path:
            raise ValueError(
                f"Data structure change: Multiple weapon modules with different asset paths found: {last_weapon_module_asset_path} and {weapon_module_asset_path}."
            )
        last_weapon_module_asset_path = weapon_module_asset_path

    weapon_module_id = CharacterModule.get_from_asset_path(last_weapon_module_asset_path)
    return weapon_module_id

def p_collision_component(data):
    data = asset_path_to_data(data["ObjectPath"])
    if 'Properties' not in data:
        return
    props = data["Properties"]

    key_to_parser_function = {
        "SphereRadius": "value",
        "AreaClassOverride": None,
        "bUseSystemDefaultObstacleAreaClass": None,
        "BodyInstance": None,
        "CapsuleHalfHeight": "value",
        "CapsuleRadius": "value",
        "RelativeScale3D": "value",
        "bTraceComplexOnMove": None,
        "StaticMesh": None,
        "bHiddenInGame": None,
    }

    return process_key_to_parser_function(key_to_parser_function, props, log_descriptor="CollisionComponent", set_attrs=False, default_configuration={
        'target': ParseTarget.MATCH_KEY
    })

def p_transf_sphere_component(data: dict):
    data = asset_path_to_data(data["ObjectPath"])
    if 'Properties' not in data:
        return
    props = data["Properties"]
    return {
        'SphereRadius': props.get('SphereRadius')
    }

def p_buffs(data: dict):
    parsed_buffs = []
    for buff in data:
        parsed_buff = {
            "Target": parse_colon_colon(buff["Value"]["Target"]),
            "BuffLingerTime": buff["Value"]["BuffLingerTime"]
        }

        buff_asset_path = buff["Key"]
        buff_data = p_actor_class(buff_asset_path)
        if buff_data:
            parsed_buff.update(buff_data)

        parsed_buffs.append(parsed_buff)

    return parsed_buffs

def p_buff_area_component(data: dict):
    data = asset_path_to_data(data["ObjectPath"])
    if 'Properties' not in data:
        return
    props = data["Properties"]
    
    key_to_parser_function = {
        "Buffs": p_buffs,
    }

    return process_key_to_parser_function(
        key_to_parser_function,
        props,
        log_descriptor="BuffAreaComponent",
        set_attrs=False
    )

def p_prevent_focus(data: dict):
    return [parse_colon_colon(elem) for elem in data]

def p_modifier(data):
    if isinstance(data, dict):
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return
        props = data["Properties"]
        return props["Value"]
    else:
        return data

def p_ability_classes(data: dict):
    ids = []
    for ability_class in data:
        ability_id = Ability.get_from_asset_path(ability_class["ObjectPath"])
        ids.append(ability_id)
    return ids

def p_weapon_selectors(data: list):
    weapon_selectors = []
    for ws in data:
        tag = ws["ModuleTag"]
        if tag is None:
            continue
        module_tag_id = ModuleTag.get_from_asset_path(tag["ObjectPath"])
        weapon_selectors.append({"module_tag_id": module_tag_id})

    if weapon_selectors:
        return weapon_selectors
    
def p_ability_selectors(data: list):
    ability_selectors = []
    for aselector in data:
        allowed_placement_types = []
        for aptype in aselector["AllowedPlacementTypes"]:
            allowed_placement_types.append(parse_colon_colon(aptype))
        module_tags = []
        for mtag in aselector["ModuleTags"]:
            module_tag_id = ModuleTag.get_from_asset_path(mtag["ObjectPath"])
            module_tags.append({"module_tag_id": module_tag_id})
        
        ability_selector = {}
        if allowed_placement_types:
            ability_selector["allowed_placement_types"] = allowed_placement_types
        if module_tags:
            ability_selector["module_tags"] = module_tags
        ability_selectors.append(ability_selector)

    if ability_selectors:
        return ability_selectors
    
def p_module_tag_selector(data: list):
    module_tags = []
    for elem in data:
        module_tag_id = ModuleTag.get_from_asset_path(elem["ObjectPath"])
        module_tags.append({"module_tag_id": module_tag_id})
    return module_tags
    
def p_module_tag_selector_or(data: list):
    module_tags = p_module_tag_selector(data)
    if module_tags:
        return {"list_operator": "Or", "module_tags": module_tags}

def p_actor_class(data: dict):
    if type(data) is list:
        for elem in data:
            return p_actor_class(elem)
    elif type(data) is dict:
        data = asset_path_to_data(data["ObjectPath"])
    elif type(data) is str:
        # is an asset path
        data = asset_path_to_data(data)
    else:
        raise ValueError("Invalid data format")

    if 'ClassDefaultObject' in data:
        data = asset_path_to_data(data["ClassDefaultObject"]["ObjectPath"])
    if 'Properties' not in data:
        return
    props = data["Properties"]

    key_to_parser_function = {
        "MuzzleSocketName": None,
        "OverlayFx": None,
        "Fade Out Time": None, #implied for vfx
        "Overlay Mesh Fx": None,
        "AmmoPartToAdd": "value",
        "CounterattackAkEvent": None, #sound
        "PrimaryChannelModificator": "value",
        "CriticalDamageChance": "value",
        "CriticalDamage": "value",
        "AdditionalProgress": "value", #red alert 7%
        "bRemoveOnDestruction": None, #+5% shield boost Flanker2
        "ShieldHealth": "value",
        "ModifierFactor": "value",
        "EffectParams": None, #vfx
        "bPrivateSpotting": "value", #emma james ult
        "SpottedSoundEvent": None, #voiceline
        "bPlayActiveSoundOnSourceActor": None, #vl
        "ModuleTagsOr": (p_module_tag_selector_or, "module_tag_selector"),
        "WeaponSelectors": p_weapon_selectors,
        "AbilitySelectors": p_ability_selectors,
        "AbilityGearGrowModifier": "value",
        "Stream": "value",
        "UltimateChargeAddition": "value",
        "NiagaraSystemInstance": None,
        "NiagaraVarName_FadeOut": None,
        "NiagaraVarName_Radius": None,
        "NiagaraRadius_Titan": None,
        "NiagaraRadius_Mech": None,
        "Effect": None, #vfx
        "Regen amount": "value",
        "bIsActiveSoundEventOneShot": None, 
        "OutgoingDamageMultiplier": None, #double damage powerup has this as 1.2x, but also 2x Modifiers, so ignoring this
        "Modifier": p_modifier,
        "DurationParamName": None,
        "OvertipFX": None,
        "DeactivationSoundEvent": None,
        "ExplosionSoundEvent": None,
        "CapsuleHalfHeight": "value",
        "CapsuleRadius": "value",
        "BodyInstance": None,
        "RelativeLocation": "value",
        "UberGraphFrame": None,
        "ExplosionFX": None,
        "DropSoundEvent": None,
        "AvoidMarker": None,
        "Damage": None, # iron rain bulgasari has empty values in here, so think its unused
        "ImpactExplosionSettings": None, #FX
        "DamageContext": None,
        "MeshComponent": None,
        "ActivationSoundEvent": None,
        "StopActivationSoundEvent": None,
        "ActivationFx": None,
        "ActivationFxRotation": None,
        "RayTracingGroupId": None,
        "ReloadTimeFactor": "value",
        "Modifiers": p_modifiers,
        "MeshFX": None,
        "SocketToFX": None,
        "MeshFXClass": None,
        "StatusFXManager": None,
        "Lifetime": "value",
        "InitialLifetime": None, # duplicate to Lifetime value
        "Icon": (parse_image_asset_path, "icon_path"),
        "PreventFocusFor": p_prevent_focus,
        "CountermeasuresEffect": None, #vfx griffin
        "NewDamageDistribution": None, #contains no data, griffin
        "Min Health": "value", #griffin
        "FriendColor": None,
        "HealingHostileColor": None,
        "HealingFriendColor": None,
        "activeEfficiency": "value", #lancelot
        "ActiveEffectSocketName": None,
        "ActiveEffectFx": None,
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
        "AoeDamage": parse_editor_curve_data,
        "DirectDamagePerSecond": "value",
        "AoeDamagePerSecond": parse_editor_curve_data,
        "TickInterval": "value",
        "DamageExplosionSettings": None, #FX
        "Owner": None,
        "CameraFXDestroyPolicy": None,
        "Undying Buff Class": None, #used by ravana
        "Damage Reduction Quotient": "value",
        "UndyingLingerTime": "value",
        "Radius": "value",
        "Height": "value",
        "BuffAreaComponent": p_buff_area_component,
        "HealingColorDelay": None, #FX
        "HealingColorFadeOutDur": None, #FX
        "Radius": "value",
        "BuffSphereComponent": None, #lancelot, shows Me and AlliesAndMeExceptTitan as buff targets, choosing to ignore this grudgingly
        "DecalComponent": None, #cosmetic
        "ParentComponent": None, #lancelot
        "HealthComponent": None, #ares. seems to reference function to detect when health is 0, so probably for starting the animation of the gun going down
        "SceneComponent": None,
        "HitSoundEvent": None,
        "Health": "value",
        "bReplicateMovement": "value",
        "RemoteRole": None,
        "InitialLifeSpan": "value",
        "Sphere Radius": "value",
        "AimBeamFX": None, #alpha ult
        "AimGroundFX": None,
        "MainDamageBeamFX": None,
        "MainDamageGroundFX": None,
        "ColorIdParam": None,
        "ThinBeamSoundEvent": None,
        "ThickBeamSoundEvent": None,
        "VictimReactionOnSpawn": None,
        "ActiveEffect": None, #legit only Matriarch ult, contains color info so just FX
        "StackDamagePercent": "value", #purifier
        "Owner": None,
        "Exclusion": None,
        "RootComponent": None,
        "EffectColorName": None,
        "DestroyReaction": None,
        "HostileColor": None,
        "CorpseDuration": None,
        "AppearSoundEvent": None,
        "DisappearSoundEvent": None,
        "DebuffVfx": None,
        "PrimaryActorTick": None, #contains bCanEverTick=true for ravana
        "SpeedIncrement": "value", # sprint boost
        "bRegenInAbsoulute": "value", #quick repair start
        "ArmorRegenPerSecond": "value",
        "RegenInterval": "value",
        "bRemoveOnDamage": "value",
        "bRemoveOnFull": "value",
        "ArmorZonesByPriority": p_armor_zones,
        "NiagaraSystem": None,
        "ArmorRegenChannel": None,
        "ShieldRegenChannel": None,
        "PPMaterial": None, #material instance for flashbang fx
        "Field Width": "value", #energy wall
        "NeutralColor": None,
        "IgnoredActorType": None, #would include this, but its an integer code, 1 for energy wall which i presume represents allies, but not worth including guesswork
        "ShieldRegenPerSecond": "value",
        "bRegenMoreDamagedZone": "value", # interesting for mesa
        "TickInterval": "value",
        "DamageDistribution": None, #gamma beam, references blank file
        "ActiveEfficiencyPercent": "value", # fuel burn
        "DurationParam": None,
        "GroundedMeshFXs": None,
        "AttacherReactionOnAttach": None, #voiceline
        "OwnerReactionOnAttach": None,
        "WeaponFX": None,
        "CountStack": "value", #ceres
        "RequiredCharForBoost": "value",
        "MaxStacks": "value",
        "BeamFX": None, # cyclops
        "ImpactFX": None,
        "BeamSoundEvent": None,
        "EndPlayAkEvent": None,
        "BeamSoundMaxDistance": None,
        "DamageDelayTime": "value",
        "Size": None, # atrophy, has x=0, y=0, z=0 so not using
        "bOverrideScheduleSettings": "value",
        "FallingSettings": "value",
        "bAlwaysRelevant": None,
        "ActivationDelay": "value", #camouflage web
        "RootCollision": None,
        "MovementComponent": p_movement_component,
        "Mesh": None,
        "StartSoundEvent": None,
        "EndSoundEvent": None,
        "GlitchSoundEvent": None,
        "SphereVFX": None,
        "DestroyVFX": None,
        "VFXRadiusOffset": None,
        "StartImpulseHorizontal": "value",
        "StartImpulseVertical": "value",
        "PathCurve": None, #galvanic screen uses tangent EditorCurveData, ignoring for now. #TODO
        "DamageApplier": p_damage_applier,
        "PerModuleColliderComponent": None,
        "OpenTime": "value", #ghost turret
        "DesiredDamage": "value",
        "FocusComponent": p_focus_component,
        "PassiveWeaponComponent": None, #contains no data
        "SoundSystemComponent": None,
        "WeaponInfos": p_weapon_infos,
        "EnemyMaterialInstance": None,
        "FriendMaterialInstance": None,
        "bCanBeDamaged": "value",
        "ActiveRadius": "value", #minefield
        "BuffsOnHit": p_actor_class,
        "SingleExplosionSoundEvent": None,
        "FinalExplosionSoundEvent": None,
        "MineNiagaraEffect": None,
        "FinalExplosionNiagaraEffect": None,
        "ExplosionNiagaraEffect": None,
        "MineLocationEQ": None,
        "ExplosionStartSoundEvent": None, #smoke wall
        "BoxComponent": None,
        "CapsuleComponent": p_collision_component, #supressor
        "bShouldFall": "value",
        "FallingSpeed": "value",
        "MaxScanRadius": "value",
        "ScanLifetime": "value",
        "SpottingBuffClass": None,
        "DeactivationLoopSound": None, #singulators
        "CollisionComponent": p_collision_component,
        "TransfusionSphereComponent": p_transf_sphere_component,
        "spawnDuration": "value",
        "TransfusionRadius": "value",
        "TransfusionInterval": "value",
        "TransfusionSourceFx": None,
        "TransfusionSphereFx": None,
        "TransfusionRayFx": None,
        "SpawnSoundEvent": None,
        "Harpoon Shot Delay": "value", #snare
        "Snare Debuff": p_actor_class,
        "Harpoon Direct Damage": "value",
        "Snap Object Types": None,
        "Death VFX": None,
        "Snare Rope VFX": None,
        "Snare Bones": None,
        "Start Sound": None,
        "End Sound": None,
        "Tracking Radius": "value",
        "Un Tracking Offset": "value",
        "bReplicates": "value",
        "Pull Force Magnitude": "value",
        "Snare VFX": None,
        "EnemyColor": None,
        "CollisionMeshComponent": None, #nanite field vfx i think
        "DisappearNaniteFX": None,
        "TransitionTime": "value", #tyr
        "DroneMaterial": None,
        "AuraMesh": None,
        "DroneSkeletalMesh": None,
        "StartHealingSoundEvent": None,
        "StopHealingSoundEvent": None,
        "FriendlyColor": None,
        "Buff": p_actor_class,
        "WasSpottedSoundEvent": None, #echo burst
        "SpottedSoundEvent": None,
        "bIndestructible": "value", #ares torso
        "SphereRadius": "value", #ceres torso
        "AttachParent": None,
        "bGenerateOverlapEvents": "value", #grim snare
        "AreaClassOverride": None, #tyr torso- basically empty path
        "bUseSystemDefaultObstacleAreaClass": None,
        "RelativeScale3D": "value",
        "RootVFX": None, #old camo web
        "SpeedMultiplier": "value", #matriarch nanite field
        "MaxAccelMultiplier": "value",
        "ArmorRegenPercentPerSecond": "value",
        "AbilityClasses": p_ability_classes, #orbital strike powerup
        "MaxAbilitiesInvocationsCount": "value",
        "ProjectileArmorDamageMult": "value",
        "ProjectileShieldDamageMult": "value",
        "bApplyMeshFxToAllModules": None,
        "SocketToFX_ColorId": None,
        "WeaponSoundComponent": None,
        "Tracker": None,
    }

    parsed_data = process_key_to_parser_function(
        key_to_parser_function, props, log_descriptor="ActorClass", set_attrs=False, default_configuration={
            'target': ParseTarget.MATCH_KEY
        }
    )

    return parsed_data