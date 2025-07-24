# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object, ParseTarget
from parsers.ability import Ability
from utils import asset_path_to_data, parse_colon_colon

class CharacterModule(Object):
    objects = dict()  # Dictionary to hold all CharacterModule instances
    
    def _parse(self):
        class_default_object = self.source_data["ClassDefaultObject"]
        cdo_data = asset_path_to_data(class_default_object["ObjectPath"])
        props = cdo_data["Properties"]
        
        key_to_parser_function = {
            "RootComponent": None,
            "ModuleScaler": self._p_module_scalar, # attrs will be set in the nested functions
            "Components": None,
            "Abilities": self._p_abilities,
            "MovementType": None, # too complicated to bother with; contains movement data as curve tables
            "FootstepSettings": None,
            "DefaultMaxSpeed": "value",
            "LandingSoundEvent": None,
            "ChassisSoundType": None,
            "SecondaryAnimationsSoundParams": None,
            "HangarAnimInstanceClass": None,
            "TorsoSocket": None,
            "DefaultMobility": "value",
            "EngineOverloadSoundParams": None,
            "LegSocketNames": None,
            "CameraParameters": None,
            "TowerRotationChannel": None,
            "DeathSoundEvent": None,
            "TowerRotationStartSound": None,
            "TowerRotationStopSound": None,
            "ClipSize": "value",
            "TimeToReload": "value",
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
            "FireModes": self._p_fire_modes, # attrs will be set in the nested functions
            "HapticFeedbackData": None,
            "ShotSoundEvent": None,
            "ReloadingStartSoundEvent": None,
            "ReloadingFinishSoundEvent": None,
            "ChunkReloadStartAudioHandlingType": None,
            "ReloadType": parse_colon_colon,
            "Adapters": self._p_adapters,
            "ZoomType": None,
            "ChunkReloadedSoundEvent": None,
            "ChargeStartedSoundEvent": None,
            "ChargeFinishedSoundEvent": None,
            "ChargedSoundEvent": None,
            "FireStartedSoundEvent": None,
            "FireStoppedSoundEvent": None,
            "ReloadChunkSize": "value",
            "bAllowAssistanceTrajectoryPrediction": ("value", "allow_assistance_trajectory_prediction"),
            "ReloadingStartedSingleSoundEvent": None,
            "BurstSoundEvent": None,
            "ChunkReloadStartedSingleSoundEvent": None,
            "ChunkReloadStartedSoundEvent": None,
            "ChunkReloadFinishedSoundEvent": None,
            "VerticalAdjustmentAngle": "value",
            "AimType": parse_colon_colon,
            "bIsPassive": ("value", "is_passive"),
            "NoShootingTime": "value",
            "AutoTargetingPolicy": parse_colon_colon,
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
            "DefaultDirectDamage": ("value", ParseTarget.MATCH_KEY),
            "DefaultAoeDamage": ("value", ParseTarget.MATCH_KEY),
            "DefaultClipSize": ("value", ParseTarget.MATCH_KEY),
            "DefaultProjectilesPerShot": ("value", ParseTarget.MATCH_KEY),
            "DefaultProjectileSpeed": ("value", ParseTarget.MATCH_KEY),
            "DefaultTimeToReload": ("value", ParseTarget.MATCH_KEY),
            "DefaultTimeBetweenShots": ("value", ParseTarget.MATCH_KEY),
            "DefaultDistanceSettings": ("value", ParseTarget.MATCH_KEY),
            "DefaultFirePower": ("value", ParseTarget.MATCH_KEY),
            "DefaultSpread": ("value", ParseTarget.MATCH_KEY),
            "DefaultLegsArmor": ("value", ParseTarget.MATCH_KEY),
            "DefaultMaxSpeed": ("value", ParseTarget.MATCH_KEY),
            "DefaultMobility": ("value", ParseTarget.MATCH_KEY),
            "DefaultFuelCapacity": ("value", ParseTarget.MATCH_KEY),
            "DefaultShieldAmount": ("value", ParseTarget.MATCH_KEY),
            "DefaultShieldRegeneration": ("value", ParseTarget.MATCH_KEY),
            "DefaultShieldDelayReduction": ("value", ParseTarget.MATCH_KEY),
            "ModuleName": None,
            "DefaultHullShare": ("value", ParseTarget.MATCH_KEY),
            "DefaultPrimaryArmor": ("value", ParseTarget.MATCH_KEY),
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
                "JumpsCount": ("value", ParseTarget.MATCH_KEY),
                "JumpPowerQuotient": ("value", ParseTarget.MATCH_KEY),
                "JumpRadius": ("value", ParseTarget.MATCH_KEY),
                "LinkedLaserEffectPrototype": None,
                "LaserDuration": ("value", ParseTarget.MATCH_KEY),
                "WhizBySettings": None,
                "DamageApplicationTime": ("value", ParseTarget.MATCH_KEY),
                "bSingleShot": ("value", ParseTarget.MATCH_KEY),
                "ConsumeAllClipOnShot": ("value", ParseTarget.MATCH_KEY),
                "ProjectileMappings": self._p_projectile_mappings,
                "ProjectileClass": None,
                "BallisticBehavior": self._p_ballistic_behavior,
                "bEnableProximityFuse": ("value", ParseTarget.MATCH_KEY),
                "ProximityFuseRadius": ("value", ParseTarget.MATCH_KEY),
                "ProjectilesPerShot": ("value", ParseTarget.MATCH_KEY),
                "ShotFX": None,
                "ShotTriggerParam": None,
                "ShotNumberParam": None,
                "TimeBetweenShots": ("value", ParseTarget.MATCH_KEY),
                "Spread": ("value", ParseTarget.MATCH_KEY),
                "AbilityChargePointsOnHit": ("value", ParseTarget.MATCH_KEY),
                "TitanChargePerHit": ("value", ParseTarget.MATCH_KEY),
                "DirectDamage": ("value", ParseTarget.MATCH_KEY),
                "AoeDamage": ("value", ParseTarget.MATCH_KEY),
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
                "BurstLength": ("value", ParseTarget.MATCH_KEY),
                "TimeBetweenBursts": ("value", ParseTarget.MATCH_KEY),
                "bOneShotEffectPerBurst": ("value", ParseTarget.MATCH_KEY),
            }
            
            return self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="BurstBehavior", set_attrs=False, tabs=2)
        
        burst_behavior_parsed_data = _p_burst_behavior(props)
        for key, value in burst_behavior_parsed_data.items():
            self.defaultable_data[key] = value

    def _p_abilities(self, list: list):
        for ability in list:
            ability_asset_path = ability["ObjectPath"]
            ability_data = asset_path_to_data(ability_asset_path)
            ability_template_asset_path = ability_data["Template"]["ObjectPath"]
            ability_id = Ability.get_from_asset_path(ability_template_asset_path)

    def _p_reload_type(self, data):
        self.reload_type = parse_colon_colon(data)  # ESWeaponReloadType::X -> X

    def _p_adapters(self, data):
        pass #TODO

    def _p_projectile_mappings(self, data):
        parsed_mappings = []
        for projectile_mapping in data:
            key_to_parser_function = {
                "MinRelativeChargeRequired": ("value", ParseTarget.MATCH_KEY),
                "MaxRelativeChargeRequired": ("value", ParseTarget.MATCH_KEY),
                "ProjectilesCount": ("value", ParseTarget.MATCH_KEY),
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
            "MinAngle": ("value", ParseTarget.MATCH_KEY),
            "MaxAngle": ("value", ParseTarget.MATCH_KEY),
            "bInvertDistanceToAngle": ("value", ParseTarget.MATCH_KEY),
            "bUseFocusComponentAlignment": ("value", ParseTarget.MATCH_KEY),
            "ProjectileClass": None,
            "HitError": ("value", ParseTarget.MATCH_KEY),
            "DistToInitialSpeed": ("value", ParseTarget.MATCH_KEY),
            "bBallisticModeForced": ("value", ParseTarget.MATCH_KEY),
        }

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="BallisticBehavior", set_attrs=False, tabs=2)
        for key, value in parsed_data.items():
            self.defaultable_data[key] = value