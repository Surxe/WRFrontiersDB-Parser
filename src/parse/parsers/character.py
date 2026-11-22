# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""The robot pawn Blueprint (BP_Character): its movement component and fuel resource.

Every game mode's DefaultPawnClass is BP_Character, and no Blueprint subclasses it, so it is
the one place the defaults every robot starts from live: the character movement component
(gravity scale, step height, walkable floor, ...) and the gameplay resources (fuel maximum and
regeneration). Values it does not set are the C++ class defaults, which the game files do not
contain. The capsule size is one of them: BP_Character's CollisionCylinder sets only navigation
flags.

Each component is merged over its archetype chain (a Blueprint stores only what it changes),
and so is the class default object, should a Blueprint ever subclass BP_Character.
"""

from parsers.object import ParseObject
from parsers.armor_zone import ArmorZone
from utils import ParseTarget, ParseAction, asset_to_data, merge_dicts, parse_colon_colon, parse_curve


def _merged_component(component_ref: dict, parse_own) -> dict:
    """A component's parsed properties merged over its archetype chain (Template)."""
    data = asset_to_data(component_ref)
    template_data = _merged_component(data["Template"], parse_own) if "Template" in data else {}
    if "Properties" not in data:
        return template_data
    return merge_dicts(template_data, parse_own(data["Properties"]))


class Character(ParseObject):
    objects = dict()

    def _parse(self):
        cdo_ref = self.source_data["ClassDefaultObject"]
        cdo_data = asset_to_data(cdo_ref)
        parsed_data = self._parse_from_data(cdo_data)
        if "Template" in cdo_data:
            parsed_data = merge_dicts(self._parse_and_merge_template(cdo_data["Template"]), parsed_data)
        for key, value in parsed_data.items():
            setattr(self, key, value)

    def _parse_from_data(self, source_data: dict):
        props = source_data.get("Properties")
        if not props:
            return {}

        key_to_parser_function = {
            # Movement
            "CharacterMovement": (self._p_movement_component, "movement_component"),
            "CapsuleComponent": (self._p_capsule_component, "capsule"),
            "RootComponent": None, #dupe of CapsuleComponent
            "bUseControllerRotationYaw": "value",
            "ResourceComponent": (self._p_resource_component, "gameplay_resources"),
            # Gameplay scalars
            "spawnDuration": ("value", "spawn_duration"),
            "TitanSpawnDuration": "value",
            "MechCollisionSpeedThreshold": "value", #robot-on-robot/object collision reactions; may only drive FX (MechCollisionEffectsBySurface), unverified
            "MinimalVerticalImpactAngle": "value", #same
            "MinImpactHeight": "value", #same, landing
            "AOEDamageToDestructiblesOnHit": parse_curve, #damage to destructible props on contact
            "DefaultLockingSystem": (self._p_locking_system, "locking_system"),
            "AimRefArmorZone": (self._p_armor_zone, "aim_ref_armor_zone_ref"),
            # Not parsed
            "HealthComponent": None, #delegates; its DestructibleArmorSettings is a global armor-destruction data asset, not movement, left for a later parse
            "DestructibleArmorComponent": None, #references HealthComponent and an armor mesh FX class
            "DefaultDamageDistribution": None, #references a data asset with no properties
            "BuffsComponent": None, #empty
            "PassiveWeaponComponent": None, #empty
            "TargetComponent": None, #empty
            "StealthComponent": None, #empty
            "AimAssistanceTargetComponent": None, #aim assist target type (Player)
            "FocusComponent": None, #UI: hp bar / nickname / outline visibility
            "DeathComponent": None, #death sequences (vfx)
            "OutgoingDamageChannel": None, #empty stat channel, modified at runtime
            "OutgoingShieldDamageChannel": None, #same
            "OutgoingArmorDamageChannel": None, #same
            "DamageDealtToHealthChannel": None, #same
            "OutgoingPeriodicDamageChannel": None, #same
            "PeriodicDamageBuffDurationChannel": None, #same
            "DashCostChannel": None, #same
            "CurveX": None, #camera spring arm
            "CurveY": None, #camera spring arm
            "CurveZ": None, #camera spring arm
            "CurveXD": None, #camera spring arm
            "CurveYD": None, #camera spring arm
            "CurveZD": None, #camera spring arm
            "DampingXCurve": None, #camera spring arm
            "DampingYCurve": None, #camera spring arm
            "DampingZCurve": None, #camera spring arm
            "RestitutionXCurve": None, #camera spring arm
            "RestitutionYCurve": None, #camera spring arm
            "RestitutionZCurve": None, #camera spring arm
            "MaxAllowdArmDisplacementPerFrame": None, #camera spring arm
            "CameraVelocityMaxDeltaTime": None, #camera
            "Current": None, #camera spring arm state
            "CameraArm3P": None, #camera
            "Camera3P": None, #camera
            "Camera1P": None, #camera
            "Camera1PPivot": None, #camera
            "CameraArtillery": None, #camera
            "CameraShakeSource1P": None, #camera shake
            "CameraShakeSource3P": None, #camera shake
            "LandedCameraShakeSettings": None, #camera shake
            "ObjectImpactCameraShakeSettings": None, #camera shake
            "CharacterViewManagerClass": None, #camera/view
            "DyingReactionClass": None, #voice line
            "TitanSpawnReactionClass": None, #voice line
            "MinTowerRotationToSound": None, #audio
            "MechCollisionEffectsBySurface": None, #sfx/vfx per surface
            "SpawnMeshFXClass": None, #vfx
            "DespawnMeshFXClass": None, #vfx
            "SpawnFX": None, #vfx
            "SpawnTitanFX": None, #vfx
            "DespawnFX": None, #vfx
            "JetpackFX": None, #vfx
            "AirControlFX": None, #vfx
            "ShieldDestructionEffect": None, #vfx
            "ShieldRestorationEffect": None, #vfx
            "ShieldEffectsCapsuleSizeParam": None, #vfx param
            "EngineForcesFXComponentClass": None, #vfx
            "SurfaceInteractionComponentClass": None, #vfx
            "WaterFXComponentClass": None, #vfx
            "OvertipFXComponent": None, #vfx
            "DefaultSkinFXDataAsset": None, #skin vfx
            "SoilingComponentClass": None, #visual dirt
            "DamagedPartsHighlightComponentClass": None, #visual
            "TreeActivationComponent": None, #foliage reaction (visual)
            "ProxyMeshOverlay": None, #mesh
            "Mesh": None, #mesh
            "OvertipWidgetComponentClass": None, #UI
            "OvertipWidgetClass": None, #UI
            "WeaponOvertipWidgetClass": None, #UI
            "WeaponOvertipWidgetOffset": None, #UI
            "SpeedometerWidgetClass": None, #UI
            "SpeedometerWidgetOffset": None, #UI
            "FuelmeterWidgetClass": None, #UI
            "FuelmeterDrawSize": None, #UI
            "FuelmeterWidgetOffset": None, #UI
            "HomingComponent": None, #homing target widget (UI)
            "TargetingHintComponentClass": None, #UI
            "MarkerClass": None, #artillery marker UI
            "ActorPingClass": None, #ping UI
            "PingComponent": None, #ping UI
            "HostilePingWheelClasses": None, #ping UI
            "FriendlyPingWheelClasses": None, #ping UI
            "SpawnCollisionHandlingMethod": None, #spawn placement
        }

        return self._process_key_to_parser_function(
            key_to_parser_function, props, log_descriptor="Character", set_attrs=False, default_configuration={
                'action': ParseAction.ATTRIBUTE,
                'target': ParseTarget.MATCH_KEY_SNAKE,
            })

    def _p_movement_component(self, data: dict):
        """SCharacterMovementComponent: every property the Blueprint sets, under the game's names."""
        def parse_own(props):
            key_to_parser_function = {
                "GravityScale": "value",
                "MaxStepHeight": "value",
                "WalkableFloorZ": "value",
                "WalkableFloorAngle": "value",
                "MaxWalkSpeed": "value",
                "MaxAcceleration": "value",
                "BrakingFrictionFactor": "value",
                "BrakingFriction": "value",
                "bUseSeparateBrakingFriction": "value",
                "GroundFriction": "value",
                "AirControl": "value",
                "AirControlBoostMultiplier": "value",
                "AirControlBoostVelocityThreshold": "value",
                "PerchRadiusThreshold": "value",
                "PerchAdditionalHeight": "value",
                "RotationRate": "value",
                "bOrientRotationToMovement": "value",
                "bUseControllerDesiredRotation": "value",
                "LedgeCheckThreshold": "value",
                "bMaintainHorizontalGroundVelocity": "value",
                "bStayBasedInAir": "value",
                "StayBasedInAirHeight": "value",
                "bUseAccelerationForPaths": "value",
                "Mass": "value",
                "JumpZVelocity": "value",
                "MaxStepHeightWhenAirborne": "value",
            }
            return self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="MovementComponent", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
        return _merged_component(data, parse_own)

    def _p_capsule_component(self, data: dict):
        """CapsuleComponent: its size, when the Blueprint sets one (BP_Character does not)."""
        def parse_own(props):
            key_to_parser_function = {
                "CapsuleRadius": "value",
                "CapsuleHalfHeight": "value",
                "AreaClassOverride": None, #navigation area
                "bUseSystemDefaultObstacleAreaClass": None, #navigation area
            }
            return self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="Capsule", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
        return _merged_component(data, parse_own) or None

    def _p_resource_component(self, data: dict):
        """SResourceComponent: one entry per resource (fuel), with its maximum and regeneration."""
        def parse_own(props):
            key_to_parser_function = {
                "GameplayResources": (self._p_gameplay_resources, "GameplayResources"),
                "FuelRestoredFullSoundEvent": None, #audio
                "FuelRestoredSoundEvent": None, #audio
                "FuelRestoredJumpSoundEvent": None, #audio
                "FuelEmptySoundEvent": None, #audio
            }
            return self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="ResourceComponent", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
        return _merged_component(data, parse_own).get("GameplayResources")

    def _p_gameplay_resources(self, data: list):
        parsed_resources = []
        for resource in data:
            key_to_parser_function = {
                "Type": parse_colon_colon,
                "MaxValue": "value",
                "RegenPerSecond": "value",
                "Value": "value", #runtime value; BeginPlay sets it to MaxValue
                "RegenBlockers": None, #runtime blocker list, empty in data
            }
            parsed_resources.append(self._process_key_to_parser_function(
                key_to_parser_function, resource, log_descriptor="GameplayResource", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                }))
        return parsed_resources

    def _p_locking_system(self, data: dict):
        def parse_own(props):
            key_to_parser_function = {
                "TimeToLockTarget": "value",
                "TimeToUnlockTarget": "value",
            }
            return self._process_key_to_parser_function(
                key_to_parser_function, props, log_descriptor="LockingSystem", set_attrs=False, default_configuration={
                    'target': ParseTarget.MATCH_KEY
                })
        return _merged_component(data, parse_own)

    def _p_armor_zone(self, data: dict):
        return ArmorZone.create_from_asset(data).to_ref()
