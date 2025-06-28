# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from utils import log, asset_path_to_data, parse_colon_colon

class CharacterModule(Object):
    objects = dict()  # Dictionary to hold all CharacterModule instances
    
    def _parse(self):
        class_default_object = self.source_data["ClassDefaultObject"]
        cdo_data = asset_path_to_data(class_default_object["ObjectPath"])
        props = cdo_data["Properties"]
        
        key_to_parser_function = {
            "RootComponent": None,
            "ModuleScaler": (self._p_module_scalar, None), # attrs will be set in the nested functions
            "Components": None,
            "Abilities": None,
            "MovementType": None, # too complicated to bother with; contains movement data as curve tables
            "DefaultMaxSpeed": ("value", "default_max_speed"),
            "LandingSoundEvent": None,
            "ChassisSoundType": None,
            "SecondaryAnimationsSoundParams": None,
            "HangarAnimInstanceClass": None,
            "TorsoSocket": None,
            "DefaultMobility": ("value", "default_mobility"),
            "EngineOverloadSoundParams": None,
            "LegSocketNames": None,
            "CameraParameters": None,
            "TowerRotationChannel": None,
            "DeathSoundEvent": None,
            "TowerRotationStartSound": None,
            "TowerRotationStopSound": None,
            "ClipSize": ("value", "clip_size"),
            "TimeToReload": ("value", "time_to_reload"),
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
            "FireModes": (self._p_fire_modes, None), # attrs will be set in the nested functions
            "HapticFeedbackData": None,
            "ShotSoundEvent": None,
            "ReloadingStartSoundEvent": None,
            "ReloadingFinishSoundEvent": None,
            "ChunkReloadStartAudioHandlingType": None,
            "ReloadType": (parse_colon_colon, "reload_type"),
            "Adapters": (self._p_adapters, "adapters"),
            "ZoomType": None,
            "ChunkReloadedSoundEvent": None,
            "ChargeStartedSoundEvent": None,
            "ChargeFinishedSoundEvent": None,
            "ChargedSoundEvent": None,
            "FireStartedSoundEvent": None,
            "FireStoppedSoundEvent": None,
            "ReloadChunkSize": ("value", "reload_chunk_size"),
            "bAllowAssistanceTrajectoryPrediction": ("value", "allow_assistance_trajectory_prediction"),
            "ReloadingStartedSingleSoundEvent": None,
            "BurstSoundEvent": None,
            "ChunkReloadStartedSingleSoundEvent": None,
            "ChunkReloadStartedSoundEvent": None,
            "ChunkReloadFinishedSoundEvent": None,
            "VerticalAdjustmentAngle": ("value", "vertical_adjustment_angle"),
            "AimType": (parse_colon_colon, "aim_type"),
            "bIsPassive": ("value", "is_passive"),
            "NoShootingTime": ("value", "no_shooting_time"),
            "AutoTargetingPolicy": (parse_colon_colon, "auto_targeting_policy"),
        }
        
        self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="CharacterModule", set_attrs=False, tabs=1)

    def _p_module_scalar(self, data):
        module_scalar_data = asset_path_to_data(data["ObjectPath"])
        if "Properties" not in module_scalar_data:
            return
        
        props = module_scalar_data["Properties"]
        # contains default damage related data that is overlayed by the FireMode and a few other smaller properties

        if not hasattr(self, 'defaultable_data'):
            self.defaultable_data = dict()

        key_to_parser_function = {
            "DefaultDirectDamage": ("value", "key"),
            "DefaultAoeDamage": ("value", "key"),
            "DefaultClipSize": ("value", "key"),
            "DefaultProjectilesPerShot": ("value", "key"),
            "DefaultProjectileSpeed": ("value", "key"),
            "DefaultTimeToReload": ("value", "key"),
            "DefaultTimeBetweenShots": ("value", "key"),
            "DefaultDistanceSettings": ("value", "key"),
            "DefaultFirePower": ("value", "key"),
            "DefaultSpread": ("value", "key"),
            "DefaultLegsArmor": ("value", "key"),
            "DefaultMaxSpeed": ("value", "key"),
            "DefaultMobility": ("value", "key"),
            "DefaultFuelCapacity": ("value", "key"),
            "DefaultShieldAmount": ("value", "key"),
            "DefaultShieldRegeneration": ("value", "key"),
            "DefaultShieldDelayReduction": ("value", "key"),
            "ModuleName": None,
            "DefaultHullShare": ("value", "key"),
            "DefaultPrimaryArmor": ("value", "key"),
        }

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="ModuleScalar", set_attrs=False, tabs=2)
        for key, value in parsed_data.items():
            key_to_store_value_in = key if 'Default' not in key else key.split('Default')[1]
            self.defaultable_data[key_to_store_value_in] = value

    def _p_fire_modes(self, data):
        if len(data) != 1:
            raise ValueError(f"Structure changed for {self.__class__.__name__} {self.id}: expected 1 FireMode, got {len(data)}")
        fire_mode = data[0]
        fire_mode_data = asset_path_to_data(fire_mode["ObjectPath"])
        firing_behavior_data = asset_path_to_data(fire_mode_data["Properties"]["FiringBehavior"]["ObjectPath"])
        props = firing_behavior_data["Properties"]
        # contains damage related data that is overlayed over the Default damage found in ModuleScalars

        if not hasattr(self, 'defaultable_data'):
            self.defaultable_data = dict()

        def _p_firing_behavior(data):
            key_to_parser_function = {
                "JumpsCount": ("value", "key"),
                "JumpPowerQuotient": ("value", "key"),
                "JumpRadius": ("value", "key"),
                "LinkedLaserEffectPrototype": None,
                "LaserDuration": ("value", "key"),
                "DamageApplicationTime": ("value", "key"),
                "bSingleShot": ("value", "key"),
                "ConsumeAllClipOnShot": ("value", "key"),
                "ProjectileMappings": (self._p_projectile_mappings, None),
                "ProjectileClass": None,
                "BallisticBehavior": (self._p_ballistic_behavior, None),
                "bEnableProximityFuse": ("value", "key"),
                "ProximityFuseRadius": ("value", "key"),
                "ProjectilesPerShot": ("value", "key"),
                "ShotFX": None,
                "ShotTriggerParam": None,
                "TimeBetweenShots": ("value", "key"),
                "Spread": ("value", "key"),
                "AbilityChargePointsOnHit": ("value", "key"),
                "TitanChargePerHit": ("value", "key"),
                "DirectDamage": ("value", "key"),
                "AoeDamage": ("value", "key"),
                "FireFX": None,
                "bContinuousFireFX": None,
                "bHasArmorVisualImpact": None,
                "bHasShieldVisualImpact": None,
                "VisualDamage": None,
                "ExplosionSettings": None,
                "CameraShakeOnHit": None,
                "HapticFeedbackData": None,
                "HealthContextBuilderClass": None,
                "BurstBehavior": None, #already parsed in burst behavior
            }

            return self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="FiringBehavior", set_attrs=False, tabs=2)

        firing_behavior_parsed_data = _p_firing_behavior(props)
        for key, value in firing_behavior_parsed_data.items():
            self.defaultable_data[key] = value

        if "BurstBehavior" not in fire_mode_data["Properties"]:
            return
        burst_behavior_data = asset_path_to_data(fire_mode_data["Properties"]["BurstBehavior"]["ObjectPath"])
        props = burst_behavior_data["Properties"]


        def _p_burst_behavior(data):
            key_to_parser_function = {
                "BurstLength": ("value", "key"),
                "TimeBetweenBursts": ("value", "key"),
                "bOneShotEffectPerBurst": ("value", "key"),
            }
            
            return self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="BurstBehavior", set_attrs=False, tabs=2)
        
        burst_behavior_parsed_data = _p_burst_behavior(props)
        for key, value in burst_behavior_parsed_data.items():
            self.defaultable_data[key] = value

    def _p_reload_type(self, data):
        self.reload_type = parse_colon_colon(data)  # ESWeaponReloadType::X -> X

    def _p_adapters(self, data):
        pass

    def _p_projectile_mappings(self, data):
        parsed_mappings = []
        for projectile_mapping in data:
            key_to_parser_function = {
                "MinRelativeChargeRequired": ("value", "key"),
                "MaxRelativeChargeRequired": ("value", "key"),
                "ProjectilesCount": ("value", "key"),
                "ProjectileClass": None,
                "FireFX": None,
                "FireSound": None,
            }

            parsed_mapping = self._process_key_to_parser_function(key_to_parser_function, projectile_mapping, log_descriptor="ProjectileMapping", set_attrs=False, tabs=2)
            parsed_mappings.append(parsed_mapping)

        return parsed_mappings

    def _p_ballistic_behavior(self, data):
        ballistic_behavior_data = asset_path_to_data(data["ObjectPath"])
        props = ballistic_behavior_data["Properties"]

        if not hasattr(self, 'defaultable_data'):
            self.defaultable_data = dict()

        key_to_parser_function = {
            "bUseFocusComponentAlignment": None,
            "MinAngle": ("value", "key"),
            "MaxAngle": ("value", "key"),
            "bInvertDistanceToAngle": ("value", "key"),
            "bUseFocusComponentAlignment": ("value", "key"),
            "ProjectileClass": None,
            "HitError": ("value", "key"),
            "DistToInitialSpeed": ("value", "key"),
            "bBallisticModeForced": ("value", "key"),
        }

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="BallisticBehavior", set_attrs=False, tabs=2)
        for key, value in parsed_data.items():
            self.defaultable_data[key] = value