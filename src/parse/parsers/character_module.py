# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.ability import Ability, p_movement_component, p_collision_component, p_actor_class
from utils import ParseTarget, asset_path_to_data, parse_colon_colon, parse_editor_curve_data, merge_dicts

class CharacterModule(Object):
    objects = dict()  # Dictionary to hold all CharacterModule instances
    
    def _parse(self):
        class_default_object = self.source_data["ClassDefaultObject"]
        cdo_data = asset_path_to_data(class_default_object["ObjectPath"])
        props = cdo_data["Properties"]

        key_to_parser_function = {
            "RootComponent": None,
            "ModuleScaler": (self._p_module_scalar, "module_scaler"),
            "ModuleLevel": "value", #no clue what this means, its an integer like 17
            "ModuleDataAsset": None, # references index 0 which ofc references this spot, so ignoring it
            "Components": None,
            "Abilities": (self._p_abilities, "abilities_ids"),
            "MovementType": None, # too complicated to bother with; contains movement data as curve tables
            "FootstepSettings": None,
            "DefaultMaxSpeed": None,
            "LandingSoundEvent": None,
            "ChassisSoundType": None,
            "SecondaryAnimationsSoundParams": None,
            "HangarAnimInstanceClass": None,
            "TorsoSocket": None,
            "DefaultMobility": None,
            "EngineOverloadSoundParams": None,
            "LegSocketNames": None,
            "CameraParameters": None,
            "TowerRotationChannel": None,
            "DeathSoundEvent": None,
            "TowerRotationStartSound": None,
            "TowerRotationStopSound": None,
            "ClipSize": None, #verified there are 0 results where clipsize is only specified here; also confirmed its always preferred in module scaler
            "TimeToReload": None, #same
            "ReloadTimeChannel": None,
            "SpreadChannel": None,
            "FireRateChannel": None,
            "OutgoingDamageChannel": None,
            "OutgoingShieldDamageChannel": None,
            "OutgoingArmorDamageChannel": None,
            "OutgoingDirectDamageChannel": None,
            "OutgoingAoeDamageChannel": None,
            "CriticalDamageChannel": None,
            "CriticalDamageChanceChannel": None,
            "CameraShakeOnFire": None,
            "FireModes": (self._p_fire_modes, "fire_modes"), # attrs will be set in the nested functions
            "HapticFeedbackData": None,
            "ShotSoundEvent": None,
            "ReloadingStartSoundEvent": None,
            "ReloadingFinishSoundEvent": None,
            "ChunkReloadStartAudioHandlingType": None,
            "ReloadType": parse_colon_colon,
            "Adapters": None,
            "ZoomType": parse_colon_colon,  # ESWeaponZoomType::X -> X
            "ChunkReloadedSoundEvent": None,
            "ChargeStartedSoundEvent": None,
            "ChargeFinishedSoundEvent": None,
            "ChargedSoundEvent": None,
            "FireStartedSoundEvent": None,
            "FireStoppedSoundEvent": None,
            "ReloadChunkSize": "value",
            "bAllowAssistanceTrajectoryPrediction": "value",
            "ReloadingStartedSingleSoundEvent": None,
            "BurstSoundEvent": None,
            "ChunkReloadStartedSingleSoundEvent": None,
            "ChunkReloadStartedSoundEvent": None,
            "ChunkReloadFinishedSoundEvent": None,
            "VerticalAdjustmentAngle": "value",
            "AimType": parse_colon_colon,
            "bIsPassive": "value",
            "NoShootingTime": "value",
            "AutoTargetingPolicy": parse_colon_colon,
            "WidgetComponent": None,
            "bShouldUseCharactersFocusTarget": "value", #tesla coil weapon
            "Muzzles": None, # list of sockets for tesla coil
            "bUseCharacterWideMuzzleSearch": "value",
            "Socket_Muzzle": None, #old tesla coil
            "bShotMuzzleSwitch": None, #vfx horde
        }

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="CharacterModule", set_attrs=False, tabs=1, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })
        
        # Store data that wasn't parsed separately into defaultable_data
        other_data = dict()
        keys_to_store_as_attrs = ['module_scaler', 'fire_modes', 'abilities_ids']
        for key, value in parsed_data.items():
            if key not in keys_to_store_as_attrs:
                other_data[key] = value
            else:
                setattr(self, key, value)

        # Only store in obj if not empty
        if other_data:
            self.misc = other_data

    def _p_module_scalar(self, data):
        module_scalar_data = asset_path_to_data(data["ObjectPath"])
        if "Properties" not in module_scalar_data:
            return
        
        props = module_scalar_data["Properties"]
        # contains default damage related data that is overlayed by the FireMode and a few other smaller properties

        parsed_module_scalers = dict()

        key_to_parser_function = {
            "AnimClass": None,
            "SkeletalMesh": None,
            "SkinnedAsset": None,
            "bReceivesDecals": "value",
            "BodyInstance": None,
            "AssetUserData": None,
            "DefaultArmor": "value",
            "DefaultShield": "value",
            "DefaultDirectDamage": "value",
            "DefaultAoeDamage": parse_editor_curve_data,
            "DefaultClipSize": "value",
            "DefaultProjectilesPerShot": "value",
            "DefaultProjectileSpeed": "value",
            "DefaultTimeToReload": "value",
            "DefaultTimeBetweenShots": "value",
            "DefaultDistanceSettings": self._p_distance_settings,
            "DefaultFirePower": "value",
            "DefaultSpread": "value",
            "DefaultLegsArmor": "value",
            "DefaultMaxSpeed": "value",
            "DefaultMobility": "value",
            "DefaultFuelCapacity": "value",
            "DefaultShieldAmount": "value",
            "DefaultShieldRegeneration": "value",
            "DefaultShieldDelayReduction": "value",
            "ModuleName": None,
            "DefaultHullShare": "value",
            "DefaultPrimaryArmor": "value",
        }

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, 
                                                           props, 
                                                           log_descriptor="ModuleScalar", 
                                                           set_attrs=False, 
                                                           tabs=2,
                                                           default_configuration={
                                                               'target': ParseTarget.MATCH_KEY
                                                           })
        for key, value in parsed_data.items():
            key_to_store_value_in = key if 'Default' not in key else key.split('Default')[1]
            parsed_module_scalers[key_to_store_value_in] = value

        return parsed_module_scalers
    
    def _p_obstacle_dmg_modifier(self, data):
        return asset_path_to_data(data["ObjectPath"])["Properties"]["Value"]

    def _p_fire_modes(self, data):
        if len(data) != 1:
            raise ValueError(f"Structure changed for {self.__class__.__name__} {self.id}: expected 1 FireMode, got {len(data)}")
        fire_mode = data[0]
        fire_mode_data = asset_path_to_data(fire_mode["ObjectPath"])

        def p_firing_behavior(data):
            data = asset_path_to_data(data["ObjectPath"])
            data = data["Properties"]
            # contains damage related data that is overlayed over the Default damage found in ModuleScalars

            key_to_parser_function = {
                "JumpsCount": "value",
                "JumpPowerQuotient": "value",
                "JumpRadius": "value",
                "LinkedLaserEffectPrototype": None,
                "LaserDuration": "value",
                "WhizBySettings": None,
                "DamageApplicationTime": "value",
                "bSingleShot": "value",
                "ConsumeAllClipOnShot": "value",
                "ProjectileMappings": self._p_projectile_mappings,
                "ProjectileClass": None, #recursive called
                "BallisticBehavior": self._p_ballistic_behavior,
                "bEnableProximityFuse": "value",
                "ProximityFuseRadius": "value",
                "ProjectilesPerShot": "value",
                "ShotFX": None,
                "ShotTriggerParam": None,
                "ShotNumberParam": None,
                "TimeBetweenShots": "value",
                "Spread": "value",
                "AbilityChargePointsOnHit": "value",
                "TitanChargePerHit": "value",
                "DirectDamage": "value",
                "AoeDamage": parse_editor_curve_data,
                "FireFX": None,
                "bContinuousFireFX": None,
                "bHasArmorVisualImpact": None,
                "bHasShieldVisualImpact": None,
                "VisualDamage": None,
                "ExplosionSettings": None,
                "CameraShakeOnHit": None,
                "HapticFeedbackData": None,
                "HealthContextBuilderClass": None,
                "HealthContextBuilder": None,
                "BurstBehavior": None, #already parsed in burst behavior
                "ChargingBehavior": None, #references data thats duplicate to whats in BurstBehavior. pulsar and bayonet use it
                "Weapon": None, # essentially empty. RetributionAutoAim uses it
                "TimeBetweenShakes": "value", #Bayonet- generally no clue what it means but its 1s
                "HalfConeAngle": "value", # tesla coil

                # seen in template only
                "ObstacleDamageModifier": self._p_obstacle_dmg_modifier,
                "CollisionComponent": p_collision_component,
                "MovementComponent": self._p_movement_component,
                "DirectDamage": "value",
                "AoeDamage": parse_editor_curve_data,
                "CanBeTransfused": None,
                "CollisionProfileName": "value",
                "MeshComponent": None,
                "GravityChangeFromDistance": parse_editor_curve_data,
                "NumberOfMulticomponent": "value",
                "TracerFX": None,
                "WaveRadiusParam": None,
                "bShowIncomingMissilesWarning": "value",
                "ImportedDistanceSettings": (self._p_distance_settings, "DistanceSettings"),
                "RootComponent": None, #scatter, points to same CollisionComponent
                "ExpansionDistanceSettingsDefault": None,
                "EffectiveDistanceSettingsDefault": None,
                "MaxDistanceSettingsDefault": None,
                "DeathDistanceSettingsDefault": None,
                "DefaultDistanceSettings": None,
                "UberGraphFrame": None,
                "AliveComponentsMaskParam": None,
                "CoordsParam": None,
                "DirectionParam": None,
                "ExplosionSoundEvent": None,
                "ExplosionFX": None,
                "DistanceSettingsCurve": parse_editor_curve_data,
                "bUseTracerOnEachComponent": "value",
                "bAlwaysRelevant": None,
                "InitialLifeSpan": "value",
                "BuffsOnHit": self._p_actor_class,
                "CruiseRollSeconds": "value",
                "HomingClimbTurnRate": "value",
                "HomingCruiseTurnRate": "value",
                "CruiseHeight": "value",
                "CruiseRollAngle": "value",
                "CruiseHeightMin": "value",
                "MaxRicochets": "value", #jigsaw
                "CorpseAttachOffset": None,
                "DestroyTracerOnceDisabled": "value",
                "CorpseTime": None,
                "DelayTime": "value", #magneto
                "VisualHitDamage": None,
                "ExplosionHitSettings": None,
                "StartOfDelaySoundEvent": None,
                "bUseGravityChangeFromDistanceCurve": "value",
                "VelocityByDistance": "value",
                "FireFX_ColorParam": None,

                # dont know where its at but it dont really matter
                "MuzzleLaserInfos": None, #vfx of horde
                "SpreadAngle": "value", #horde
            }

            # Recursively parse template if present
            if "ProjectileClass" in data:
                base = p_firing_behavior(asset_path_to_data(data["ProjectileClass"]["ObjectPath"])["ClassDefaultObject"])
            else:
                base = {}
            result = dict(base)

            overlay = self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="FiringBehavior", set_attrs=False, tabs=2, default_configuration={
                'target': ParseTarget.MATCH_KEY
            })

            return merge_dicts(result, overlay)

        def p_burst_behavior(data):
            data = asset_path_to_data(data["ObjectPath"])
            props = data["Properties"]

            key_to_parser_function = {
                "BurstLength": "value",
                "TimeBetweenBursts": "value",
                "bOneShotEffectPerBurst": "value",
            }
            
            return self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="BurstBehavior", set_attrs=False, tabs=2, default_configuration={
                'target': ParseTarget.MATCH_KEY
            })
        
        def p_charging_behavior(data):
            data = asset_path_to_data(data["ObjectPath"])
            props = data["Properties"]

            def p_charge_modifiers(data: list):
                parsed_modifiers = []
                for charge_modifier in data:
                    what = parse_colon_colon(charge_modifier["Key"])
                    ecd = parse_editor_curve_data(charge_modifier["Value"])
                    parsed_modifier = {
                        "what": what,
                        "CurveData": ecd,
                    }
                    parsed_modifiers.append(parsed_modifier)
                return parsed_modifiers

            key_to_parser_function = {
                "TimeToCharge": "value",
                "ShootOnFullCharge": "value",
                "ChargeModifiers": p_charge_modifiers,
                "ChargedShotSound": None,
            }

            return self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="ChargingBehavior", set_attrs=False, tabs=2, default_configuration={
                'target': ParseTarget.MATCH_KEY
            })

        key_to_parser_function = {
            "FiringBehavior": p_firing_behavior,
            "BurstBehavior": p_burst_behavior,
            "ChargingBehavior": p_charging_behavior,
            "SwitchingType": parse_colon_colon
        }
        
        return self._process_key_to_parser_function(key_to_parser_function, fire_mode_data["Properties"], log_descriptor="FireMode", set_attrs=False, tabs=1, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })

    def _p_movement_component(self, data):
        return p_movement_component(data)

    def _p_abilities(self, list: list):
        parsed_abilities = []
        for ability in list:
            ability_asset_path = ability["ObjectPath"]
            ability_id = Ability.get_from_asset_path(ability_asset_path)
            parsed_abilities.append(ability_id)
        return parsed_abilities

    def _p_reload_type(self, data):
        self.reload_type = parse_colon_colon(data)  # ESWeaponReloadType::X -> X

    def _p_actor_class(self, data):
        return p_actor_class(data)

    def _p_projectile_mappings(self, data):
        parsed_mappings = []
        for projectile_mapping in data:
            key_to_parser_function = {
                "MinRelativeChargeRequired": "value",
                "MaxRelativeChargeRequired": "value",
                "ProjectilesCount": "value",
                "ProjectileClass": None,
                "FireFX": None,
                "FireSound": None,
            }
            parsed_mapping = self._process_key_to_parser_function(key_to_parser_function, projectile_mapping, log_descriptor="ProjectileMapping", set_attrs=False, tabs=2, default_configuration={
                'target': ParseTarget.MATCH_KEY
            })
            parsed_mappings.append(parsed_mapping)

        return parsed_mappings

    def _p_ballistic_behavior(self, data):
        ballistic_behavior_data = asset_path_to_data(data["ObjectPath"])
        props = ballistic_behavior_data["Properties"]

        key_to_parser_function = {
            "bUseFocusComponentAlignment": None,
            "MinAngle": "value",
            "MaxAngle": "value",
            "bInvertDistanceToAngle": "value",
            "bUseFocusComponentAlignment": "value",
            "ProjectileClass": None,
            "HitError": "value",
            "DistToInitialSpeed": parse_editor_curve_data,
            "bBallisticModeForced": "value",
        }

        return self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="BallisticBehavior", set_attrs=False, tabs=2, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })
    
    def _p_distance_settings(self, data):
        parsed_distance_settings = []
        prev_interp_mode = None
        for elem in data:
            distance_state = parse_colon_colon(elem["Key"])
            parsed_distance_setting = self._p_this_distance_setting(elem["Value"])
            parsed_distance_setting["DistanceState"] = distance_state
            interp_mode = parsed_distance_setting["InterpMode"]
            if prev_interp_mode is not None and interp_mode != prev_interp_mode:
                raise ValueError(f"Inconsistent InterpModes found in DistanceSettings for {self.__class__.__name__} {self.id}: {prev_interp_mode} and {interp_mode}")
            prev_interp_mode = interp_mode
            del parsed_distance_setting["InterpMode"]
            parsed_distance_settings.append(parsed_distance_setting)
        
        return {
            "InterpMode": prev_interp_mode,
            "CurveData": parsed_distance_settings
        }

    def _p_this_distance_setting(self, data):
        key_to_parser_function = {
            "Distance": "value",
            "InterpolationMode": (parse_colon_colon, "InterpMode"),
            "DirectDamageMultiplier": "value",
        }

        return self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="DistanceSetting", set_attrs=False, tabs=2, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })