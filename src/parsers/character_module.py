# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from utils import log
from utils import asset_path_to_data

class CharacterModule(Object):
    objects = dict()  # Dictionary to hold all CharacterModule instances
    
    def _parse(self):
        class_default_object = self.source_data["ClassDefaultObject"]
        cdo_data = asset_path_to_data(class_default_object["ObjectPath"])
        props = cdo_data["Properties"]
        
        key_to_parser_function = {
            "RootComponent": None,
            "ModuleScaler": self._p_module_scalar,
            "Components": None,
            "Abilities": None,
            "MovementType": None, # too complicated to bother with; contains movement data as curve tables
            "DefaultMaxSpeed": self._p_default_max_speed,
            "LandingSoundEvent": None,
            "ChassisSoundType": None,
            "SecondaryAnimationsSoundParams": None,
            "HangarAnimInstanceClass": None,
            "TorsoSocket": None,
            "DefaultMobility": self._p_default_mobility,
            "EngineOverloadSoundParams": None,
            "LegSocketNames": None,
            "CameraParameters": None,
            "TowerRotationChannel": None,
            "DeathSoundEvent": None,
            "TowerRotationStartSound": None,
            "TowerRotationStopSound": None,
            "ClipSize": self._p_clip_size,
            "TimeToReload": self._p_time_to_reload,
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
            "FireModes": self._p_fire_modes,
            "HapticFeedbackData": None,
            "ShotSoundEvent": None,
            "ReloadingStartSoundEvent": None,
            "ReloadingFinishSoundEvent": None,
            "ChunkReloadStartAudioHandlingType": None,
            "ReloadType": self._p_reload_type,
            "Adapters": self._p_adapters,
            "ZoomType": None,
            "ChunkReloadedSoundEvent": None,
            "ChargeStartedSoundEvent": None,
            "ChargeFinishedSoundEvent": None,
            "ChargedSoundEvent": None,
            "FireStartedSoundEvent": None,
            "FireStoppedSoundEvent": None,
            "ReloadChunkSize": self._p_reload_chunk_size,
            "bAllowAssistanceTrajectoryPrediction": self._p_trajectory_prediction,
            "ReloadingStartedSingleSoundEvent": None,
            "BurstSoundEvent": None,
            "ChunkReloadStartedSingleSoundEvent": None,
            "ChunkReloadStartedSoundEvent": None,
            "ChunkReloadFinishedSoundEvent": None,
            "VerticalAdjustmentAngle": self._p_vertical_adjustment_angle,
            "AimType": self._p_aim_type,
            "bIsPassive": self._p_is_passive,
            "NoShootingTime": self._p_no_shooting_time,
            "AutoTargetingPolicy": self._p_auto_targeting_policy,
        }
        for key, value in props.items():
            if key in key_to_parser_function:
                if key_to_parser_function[key] is not None:
                    # Call the parser function with the value
                    key_to_parser_function[key](value)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'", tabs=1)

    def _p_module_scalar(self, data):
        module_scalar_data = asset_path_to_data(data["ObjectPath"])
        if "Properties" not in module_scalar_data:
            return
        
        props = module_scalar_data["Properties"]
        # contains default damage related data that is overlayed by the FireMode and a few other smaller properties

        if not hasattr(self, 'defaultable_data'):
            self.defaultable_data = dict()

        key_to_parser_function = {
            "DefaultDirectDamage": "value",
            "DefaultAoeDamage": "value",
            "DefaultClipSize": "value",
            "DefaultProjectilesPerShot": "value",
            "DefaultProjectileSpeed": "value",
            "DefaultTimeToReload": "value",
            "DefaultTimeBetweenShots": "value",
            "DefaultDistanceSettings": "value",
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

        for key, value in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function == "value":
                    self.defaultable_data[key.split('Default')[1]] = props[key] #remove "Default" from the key
                elif function is not None:
                    # Call the parser function with the value
                    function(value)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}' in ModuleScaler", tabs=2)
        
    def _p_default_max_speed(self, data):
        pass

    def _p_default_mobility(self, data):
        pass

    def _p_clip_size(self, data):
        pass

    def _p_time_to_reload(self, data):
        pass

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

        key_to_parser_function = {
            "JumpsCount": "value",
            "JumpPowerQuotient": "value",
            "JumpRadius": "value",
            "LinkedLaserEffectPrototype": None,
            "LaserDuration": "value",
            "DamageApplicationTime": "value",
            "bSingleShot": "value",
            "ConsumeAllClipOnShot": "value",
            "ProjectileMappings": self._p_projectile_mappings,
            "ProjectileClass": None,
            "BallisticBehavior": self._p_ballistic_behavior,
            "bEnableProximityFuse": "value",
            "ProximityFuseRadius": "value",
            "ProjectilesPerShot": "value",
            "ShotFX": None,
            "ShotTriggerParam": None,
            "TimeBetweenShots": "value",
            "Spread": "value",
            "AbilityChargePointsOnHit": "value",
            "TitanChargePerHit": "value",
            "DirectDamage": "value",
            "AoeDamage": "value",
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

        for key, value in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function == "value":
                    self.defaultable_data[key] = props[key]
                elif function is not None:
                    # Call the parser function with the value
                    function(value)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}' in FireMode", tabs=2)

        if "BurstBehavior" not in fire_mode_data["Properties"]:
            return
        burst_behavior_data = asset_path_to_data(fire_mode_data["Properties"]["BurstBehavior"]["ObjectPath"])
        props = burst_behavior_data["Properties"]

        key_to_parser_function = {
            "BurstLength": "value",
            "TimeBetweenBursts": "value",
            "bOneShotEffectPerBurst": "value",
        }
        for key, value in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function == "value":
                    self.defaultable_data[key] = props[key]
                elif function is not None:
                    # Call the parser function with the value
                    function(value)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}' in BurstBehavior", tabs=2)
        

    def _p_reload_type(self, data):
        self.reload_type = data.split('::')[-1]  # ESWeaponReloadType::X -> X

    def _p_adapters(self, data):
        pass

    def _p_reload_chunk_size(self, data):
        pass

    def _p_trajectory_prediction(self, data):
        pass

    def _p_vertical_adjustment_angle(self, data):
        pass

    def _p_aim_type(self, data):
        pass

    def _p_is_passive(self, data):
        pass

    def _p_no_shooting_time(self, data):
        pass

    def _p_auto_targeting_policy(self, data):
        pass

    def _p_projectile_mappings(self, data):
        pass

    def _p_ballistic_behavior(self, data):
        ballistic_behavior_data = asset_path_to_data(data["ObjectPath"])
        props = ballistic_behavior_data["Properties"]

        if not hasattr(self, 'defaultable_data'):
            self.defaultable_data = dict()

        key_to_parser_function = {
            "bUseFocusComponentAlignment": None,
            "MinAngle": "value",
            "MaxAngle": "value",
            "bInvertDistanceToAngle": "value",
            "bUseFocusComponentAlignment": "value",
            "ProjectileClass": None,
            "HitError": "value",
            "DistToInitialSpeed": "value",
            "bBallisticModeForced": "value",
        }

        for key, value in props.items():
            if key in key_to_parser_function:
                function = key_to_parser_function[key]
                if function == "value":
                    self.defaultable_data[key] = props[key]
                elif function is not None:
                    # Call the parser function with the value
                    function(value)
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}' in BallisticBehavior", tabs=2)