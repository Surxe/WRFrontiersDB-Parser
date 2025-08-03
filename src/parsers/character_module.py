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
            "ModuleLevel": "value", #no clue what this means, its an integer like 17
            "ModuleDataAsset": None, # references index 0 which ofc references this spot, so ignoring it
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
            "AnimClass": None,
            "SkeletalMesh": None,
            "SkinnedAsset": None,
            "bReceivesDecals": "value",
            "BodyInstance": None,
            "AssetUserData": None,
            "DefaultArmor": "value",
            "DefaultShield": "value",
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

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="ModuleScalar", set_attrs=False, tabs=2
                                                           , default_configuration={
                                                               'target': ParseTarget.MATCH_KEY
                                                           })
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
                "ProjectileClass": None,
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
                "HealthContextBuilder": None,
                "BurstBehavior": None, #already parsed in burst behavior
                "ChargingBehavior": None, #references data thats duplicate to whats in BurstBehavior. pulsar and bayonet use it
                "Weapon": None, # essentially empty. RetributionAutoAim uses it
                "TimeBetweenShakes": "value", #Bayonet- generally no clue what it means but its 1s
                "HalfConeAngle": "value", # tesla coil
            }

            return self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="FiringBehavior", set_attrs=False, tabs=2, default_configuration={
                'target': ParseTarget.MATCH_KEY
            })

        firing_behavior_parsed_data = _p_firing_behavior(props)
        for key, value in firing_behavior_parsed_data.items():
            self.defaultable_data[key] = value

        if "BurstBehavior" not in fire_mode_data["Properties"]:
            return
        burst_behavior_data = asset_path_to_data(fire_mode_data["Properties"]["BurstBehavior"]["ObjectPath"])
        props = burst_behavior_data["Properties"]


        def _p_burst_behavior(data):
            key_to_parser_function = {
                "BurstLength": "value",
                "TimeBetweenBursts": "value",
                "bOneShotEffectPerBurst": "value",
            }
            
            return self._process_key_to_parser_function(key_to_parser_function, data, log_descriptor="BurstBehavior", set_attrs=False, tabs=2, default_configuration={
                'target': ParseTarget.MATCH_KEY
            })
        
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

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="BallisticBehavior", set_attrs=False, tabs=2, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })
        for key, value in parsed_data.items():
            self.defaultable_data[key] = value