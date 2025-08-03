# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object, ParseTarget
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
            "AIConditions": self._p_ai_conditions,
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
            "MaxTargetingDistance": "value", #lancelot, despite it not having any targeting and iirc radius specified elsewhere
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
            "bLockOnActor": "value",
            "TargetingMarkerClass": None,
            "AssistanceRadius": None,
            "RetributionAnimTime": None,
            "WeaponInfos": self._p_weapon_infos, # ares retribution and volta tesla coil
            "ActivateWeaponsAction": self._p_activate_weapons_action,
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
            "On Collision AoE Damage": "value",
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
            "ResourceUnitsPerSecond": "value", #fuel reserve
            "ResourceType": "value",
            "CameraShakeOnDamage": None, # flashbang
            "SpawnActorCollisionHandlingMethod": None, #varangian
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=3)

    def _p_weapon_infos(self, list: list):
        log(f"Parsing weapon infos for {self.id}", tabs=4)

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
    
    def _p_activate_weapons_action(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        return self._p_weapon_infos(data["Properties"]["WeaponInfos"])

    def _p_spawn_action(self, data: dict):
        log(f"Parsing spawn action for {self.id}", tabs=4)

        spawn_action_data = asset_path_to_data(data["ObjectPath"])

        if 'Properties' not in spawn_action_data:
            return None

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
        log(f"Parsing confirmation action for {self.id}", tabs=4)

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
        log(f"Parsing projectile types for {self.id}", tabs=4)

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
                "GravityChangeFromDistance": "value",
            }

            parsed_proj = self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="ProjectileType", tabs=4, set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
            parsed_proj["SpawnSocketName"] = projectile_type["SpawnSocketName"]
            parsed_projectile_types.append(parsed_proj)

        return parsed_projectile_types
    
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
            }

            parsed_action = self._process_key_to_parser_function(
                key_to_parser_function, action_data, log_descriptor="Action", tabs=4, set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                }
            )

            parsed_actions.append(parsed_action)

        return parsed_actions

    def _p_max_speed_modifier(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if "Properties" not in data:
            return None
        parsed_data = dict()
        if "Value" in data["Properties"]:
            parsed_data["Value"] = data["Properties"]["Value"]
        if "Type" in data["Properties"]:
            parsed_data["Type"] = parse_colon_colon(data["Properties"]["Type"])
        return parsed_data
    
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
                "Owner": None,
                "CameraFXDestroyPolicy": None,
                "Undying Buff Class": None, #used by ravana
                "Damage Reduction Quotient": "value",
                "UndyingLingerTime": "value",
                "Radius": "value",
                "Height": "value",
                "BuffAreaComponent": None,
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
                "ArmorZonesByPriority": self._p_armor_zones,
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

    def _p_stat(self, data: dict):
        stat_id = ModuleStat.get_from_asset_path(data["ObjectPath"])
        return stat_id
    
    def _p_armor_zones(self, list: dict):
        armor_zone_names = []
        for elem in list:
            armor_zone_asset_path = elem["ObjectPath"]
            # armor zone file does not contain any front-facing information, so instead going to use the file name as a reference here
            armor_zone_name = armor_zone_asset_path.split("DA_ArmorZone_")[-1].split(".")[0] #../DA_ArmorZone_Torso.0 -> Torso
            armor_zone_names.append(armor_zone_name)
        return armor_zone_names
    
    def _p_pushing_settings(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return None
        else:
            return data["Properties"]
        
    def _p_charge_trigger(self, data: dict):
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return None
        return data["Properties"]