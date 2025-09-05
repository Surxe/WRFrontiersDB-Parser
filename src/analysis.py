import sys
import os
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, PARAMS


class Analysis:
    def __init__(self, module_class, character_module_class, module_stat_class):
        self.module_class = module_class
        self.character_module_class = character_module_class
        self.module_stat_class = module_stat_class

        self.calc_modules_dps(self.module_class, self.character_module_class)

        res = self.get_level_diffs_per_module(self.module_class.objects)
        self.level_diffs_by_module = res['level_diffs']
        distinct_stat_keys = res['distinct_stat_keys']
        self.total_upgrade_cost_for_all_modules = res['total_upgrade_costs']

        stat_ranks = self.get_ranks_per_stat(self.level_diffs_by_module, self.module_stat_class.objects, distinct_stat_keys)

        ranks_per_module = self.get_ranks_per_module(stat_ranks, module_ids=self.level_diffs_by_module.keys())
        for module_id, rank in ranks_per_module.items():
            self.level_diffs_by_module[module_id]['stats_percentile'] = rank

        self.level_diffs_by_stat = self.get_level_diffs_per_stat(self.level_diffs_by_module, stat_ranks)

    ##########################
    #           DPS          #
    ##########################
    def calc_modules_dps(self, module_class, character_module_class):
        core_dps_keys = ["RoundsPerMinute", "TimeToReload", "ClipSize"]

        for module_id, module in module_class.objects.items():
            shot_damage_keys = ['DamageArmor', 'DamageNoArmor', 'AoeArmor', 'AoeNoArmor']
            if not any(module._get_level_attr(0, key) for key in shot_damage_keys):
                continue #only calculate if the module actually has a dps stat in constants or variables at lvl0
            #only calculate if the module actually has a dps stat in constants or variables at lvl0
            # this check is first to avoid unnecessary processing for non-dps modules

            module_scalars = module.levels.get('module_scalars')
            if module_scalars is None:
                return #cannot calc dps if no levels data
            
            # Retrieve the character_module attrs that affect dps
            has_multiple_character_modules = len(module.character_module_mounts)>1 #these are usually 2 shoulder mounts or even 2 weapon mounts for matriarch's Hive
            # Not going to calc dps for each possible mount, so instead were going to check if this case even has dps specific attrs in the cm

            for cm_mount in module.character_module_mounts:
                cm_id = cm_mount["character_module_id"]
                character_module = character_module_class.objects[cm_id]

                def get_charge_behavior(cm):
                    fire_modes = getattr(cm, 'fire_modes', None)
                    if not fire_modes:
                        return None
                    charging_behavior = fire_modes.get('ChargingBehavior')
                    if not charging_behavior:
                        return None
                    parsed_charging_behavior = {}

                    for k, v in charging_behavior.items():
                        if k == 'TimeToCharge':
                            parsed_charging_behavior[k] = v
                        elif k == 'ShootOnFullCharge':
                            pass #doesnt affect dps, just gameplay
                        elif k == 'ChargeModifiers': #only add the charge modifier that affects damage
                            for charge_modifier in v:
                                what = charge_modifier['what']
                                if what == 'Damage':
                                    parsed_charging_behavior['ChargeModifier'] = {
                                        'what': 'ShotDamage',
                                        'CurveData': charge_modifier['CurveData']
                                    }
                                    break
                                elif what in ['VerticalSpread', 'HorizontalSpread']:
                                    pass #confirmed to not affect dps
                                else:
                                    log(f"Warning: Unhandled charge modifier what {what} in module {module_id} character module {cm_id}. Unknown if it affects dps.")
                        else:
                            log(f"Warning: Unhandled charge behavior key {k} in module {module_id} character module {cm_id}")

                    return parsed_charging_behavior

                def get_burst_behavior(cm):
                    fire_modes = getattr(cm, 'fire_modes', None)
                    if not fire_modes:
                        return None
                    burst_behavior = fire_modes.get('BurstBehavior', None)
                    if not burst_behavior:
                        return None
                    parsed_burst_behavior = {}
                    for k, v in burst_behavior.items():
                        if k in ['BurstLength', 'TimeBetweenBursts']:
                            parsed_burst_behavior[k] = v
                        elif k == 'bOneShotEffectPerBurst':
                            pass #vfx/voicequeue i think
                        else:
                            log(f"Warning: Unhandled burst behavior key {k} in module {module_id} character module {cm_id}")
                    return parsed_burst_behavior

                def get_reload_type(cm):
                    misc = getattr(cm, 'misc', None)
                    if not misc:
                        return None
                    reload_type = misc.get('ReloadType', None)
                    return reload_type
                
                def get_no_shooting_time(cm):
                    misc = getattr(cm, 'misc', None)
                    if not misc:
                        return None
                    no_shooting_time = misc.get('NoShootingTime', None)
                    return no_shooting_time
                
                charge_behavior = get_charge_behavior(character_module)
                burst_behavior = get_burst_behavior(character_module)
                reload_type = get_reload_type(character_module)
                no_shooting_time = get_no_shooting_time(character_module)

                if has_multiple_character_modules and (charge_behavior or burst_behavior or reload_type or no_shooting_time):
                    raise NotImplementedError(f"Module {module_id} has multiple character module mounts and one or more ({cm_id}) has dps behavior (charge, burst, reload type, or no shooting time) that is not currently supported for DPS calculation.")
                # will always be the last iteration, no break necessary

            log(f"Calculating DPS for module: {module_id}")

            reload_type = reload_type if reload_type else 'Magazine' #default to magazine if not specified

            # Get the levels data and calculate dps for each level
            num_levels = 1 if 'variables' not in module_scalars else len(module_scalars['variables'])
            for level_index in range(num_levels):
                core_dps_data = {k: module._get_level_attr(level_index, k) for k in core_dps_keys} #get dps values
                if not all(v is not None for v in core_dps_data.values()):
                    continue #skip if any required stat is missing

                for shot_damage_key in shot_damage_keys:
                    core_dps_with_shot_damage = core_dps_data.copy()
                    core_dps_with_shot_damage['ShotDamage'] = module._get_level_attr(level_index, shot_damage_key)

                    dps = self.calculate_dps(core_dps_with_shot_damage, charge_behavior, burst_behavior, reload_type, no_shooting_time)

    @staticmethod
    def calculate_dps(core_dps_data, charge_behavior, burst_behavior, reload_type, no_shooting_time):
        """
        Calculate all applicable variations of DPS (Damage Per Second) for a weapon based on its core stats and behaviors.
        
        Args:
            core_dps_data (dict): 
                RoundsPerMinute (int): Number of rounds fired per minute.
                TimeToReload (float): Time taken to reload after emptying the clip.
                ClipSize (int): Number of bullets in a clip.
                ShotDamage (float): shot_damage per trigger/left-click.

            charge_behavior (str): Charge behavior of the weapon.
                TimeToCharge (float): Time taken to fully charge the weapon.
                ChargeModifier (dict):
                    what (str): What the charge modifier modifies.
                    CurveData (list): List of points
                        point (dict): A point in the curve.
                            Time (float) : Percentage of TimeToCharge it was charged for.
                            Value (float): Multiplier at this charge time.
                            InterpMode (str): Interpolation mode between the previous point and this one. (usually 'RCIM_Linear')

            burst_behavior (dict): Burst behavior of the weapon.
                BurstLength (int): Number of shots in a burst.
                TimeBetweenBursts (float): Time between bursts. Reload can also start/continue during this time.

            reload_type (str): Reload type of the weapon. 
                'Magazine' for reloading at the end of the magazine
                'ReloadWhileFire' for reloading constantly while firing/charging, even during no_shooting_time
            
            no_shooting_time (float): Time during which the weapon cannot shoot nor charge (the latter is the important part).

        Returns:
            dict: {
                "InstantDPS": float,
                "ClipDPS": float,
                "CycleDPS": float,
                "InfiniteAmmo_CycleDPS": float, (if differs to CycleDPS)
                "Uncharged_InstantDPS": float, (if charge_behavior is defined)
                "Uncharged_ClipDPS": float, (if charge_behavior is defined)
                "Uncharged_CycleDPS": float, (if charge_behavior is defined)
                "Uncharged_InfiniteAmmo_CycleDPS": float, (if charge_behavior is defined) (if differs to Uncharged_CycleDPS)
                "FullyCharged_InstantDPS": float, (if charge_behavior is defined)
                "FullyCharged_ClipDPS": float, (if charge_behavior is defined)
                "FullyCharged_CycleDPS": float, (if charge_behavior is defined)
                "FullyCharged_InfiniteAmmo_CycleDPS": float, (if charge_behavior is defined) (if differs to FullyCharged_CycleDPS)
                "IdeallyCharged_InstantDPS": float, (if charge_behavior is defined)
                "IdeallyCharged_ClipDPS": float, (if charge_behavior is defined)
                "IdeallyCharged_CycleDPS": float, (if charge_behavior is defined) (if charge_behavior is defined)
                "IdeallyCharged_InfiniteAmmo_CycleDPS": float, (if charge_behavior is defined) (if differs to IdeallyCharged_CycleDPS)
            }

        DPS Measurements:
            TimeToEmptyClip: Time taken to fire all shots in the clip. If ReloadType is 'ReloadWhileFire', this includes any reloaded rounds that occurs during firing.
            InstantDPS: Damage per second assuming continuous fire with no reloads (t=0)
            ClipDPS: Damage per second assuming continuous fire until the clip is empty (t=TimeToEmptyClip).
            CycleDPS: Damage per second assuming continuous fire including reloads (t=TimeToEmptyClip + TimeToReload)
            InfiniteAmmoCycleDPS: Damage per second assuming continuous fire including reloads but with infinite ammo (t=TimeToEmptyClip + TimeBetweenBursts). Only populated if it differs to CycleDPS. 
        Charge Measurements:
            Uncharged: No charge time, minimal damage modifier (if applicable, otherwise 1x)
            Fully Charged: Full charge time, full damage modifier (if applicable, otherwise 1x)
            Ideally Charged: Charge time equal to TimeBetweenShots - NoShootingTime. Damage modifier at this charge time (if applicable, otherwise 1x)
        Example metrics:
            ChargeModifier (dict):
                "what": "Damage",
                "CurveData": [
                    {
                        "Time": 0.0,
                        "Value": 0.1,
                        "InterpMode": "RCIM_Linear"
                    },
                    {
                        "Time": 0.3,
                        "Value": 0.32394993,
                        "InterpMode": "RCIM_Linear"
                    },
                    {
                        "Time": 0.90243274,
                        "Value": 0.96810997,
                        "InterpMode": "RCIM_Linear"
                    },
                    {
                        "Time": 1.0,
                        "Value": 1.0,
                        "InterpMode": "RCIM_Linear"
                    }
                ]
                - Uncharged: 0.1x damage modifier
                - Fully Charged: 1.0x damage modifier
                - Ideally Charged: Linear interpolation between the two points on either side of Time=(TimeBetweenShots - NoShootingTime). Same as Uncharged for Shocktrain since TimeBetweenShots=NoShootingTime.
            
        Note: These measurements assume perfect accuracy and do not account for factors like aim time, movement, or environmental conditions.

        Examples: (numbers will not be updated in the future, use them as examples only)
            Standard Weapon - Punisher:
                - TimeBetweenShots: 0.58s
                - ClipSize: 95
                - TimeToReload: 5.52s
                - ReloadType: Magazine
                - On each shot:
                    1. Shoot (instantaneous)
                    2.1. If clip empty, reload for 5.52s (TimeToReload)
                    2.2. If clip not empty, wait for 0.58s (TimeBetweenShots)
                    3. Repeat from step 1.
                    - (1 shot per 0.58s)
                    - Instant DPS: 1 shot/0.58s
                    - Clip DPS: 95 shots/(0.58s*94) = 1 shot/0.573s
                    - Cycle DPS: 95 shots/(0.58s*94 + 5.52s) = 1 shot/0.623s


            Charge Weapon - Shocktrain:
                - NoShootingTime: 0.4s
                - TimeBetweenShots: 0.4s
                - TimeToCharge: 1.4s
                - ReloadType: ReloadWhileFire
                - On each shot:
                    1. Charge for up to 1.4s (can shoot earlier but less damage)
                    2. Shoot (instantaneous)
                    3. Wait for 0.4s (NoShootingTime) and 0.4s (TimeBetweenShots) simultaneously
                    4. Charging can begin again. (repeat from step 1)
                    - Reload never pauses and is not interrupted by charging


            Charge Weapon - Fowler:
                - NoShootingTime: 0s (not defined)
                - TimeBetweenShots: 0.75s
                - TimeToCharge: 1.1s
                - ReloadType: Magazine
                - ClipSize: 10
                - TimeToReload: 3.61s
                - On each shot (not charged at all):
                    1. Shoot (instantaneous)
                    2.1. If clip empty, reload
                    2.2. If clip not empty, wait for 0.75s (TimeBetweenShots)
                    3. Repeat from step 1.
                    - (1 uncharged shot per 0.75s)
                    - Instant DPS: 1 shot/0.75s
                    - Clip DPS: 10 shots/(0.75s*9) = 1 shot/0.675s
                    - Cycle DPS: 10 shots/(0.75s*9 + 3.61s) = 1 shot/0.93s
                - Or on each shot (Fully charged):
                    1. Charge for 1.1s
                    2. Shoot (instantaneous)
                    3.1. If clip empty, reload
                    3.2. If clip not empty, wait for 0.75s (TimeBetweenShots)
                    4. Repeat from step 1.
                    - (1 fully charged shot per 1.85s)
                    - Instant/Clip/Cycle DPS you can use the same formulas as above but with 1.85s instead of 0.75s
                - On each shot (Ideal):
                    1. Charge for up to 1.1s (first bullet is not apart of the "ideal"ness)
                    2. Shoot (instantaneous)
                    3. Begin charging again for 0.75s (TimeBetweenShots, NOT TimeToCharge)
                    4.1. If clip empty, reload
                    5. Repeat from step 2.
                    - (1 shot charged for 0.75s per 0.75s assuming perfect timing)
                    - Instant/Clip/Cycle DPS you can use the same formulas as above
                

            Burst Weapon - MLX2:
                - NoShootingTime: 0s (not defined)
                - ClipSize: 5
                - TimeBetweenShots: 0.05s
                - ReloadType: Magazine
                - TimeToReload: 4.49s
                - BurstLength: 5 (shots)
                - TimeBetweenBursts: 1.3s
                - On each shot (generic):
                    1. Shoot instantaneously
                    2. Wait for 0.05s (TimeBetweenShots)
                    3. Repeat from step 1 until clip is empty or BurstLength shots have been fired (checked in this order)
                    3.1 If clip is empty: Wait 4.49s (TimeToReload)
                    3.2 If BurstLength shots have been fired and clip was not first empty: Wait 1.3s (TimeBetweenBursts)
                    4. Repeat from step 1.
                - Without infinite ammo:
                    1. Shoot instaneously
                    2. Wait for 0.05s (TimeBetweenShots)
                    3. Repeat from step 1 until clip is empty (5 shots total)
                    3.1. Clip is now empty: Wait 4.49s (TimeToReload)
                    4. Repeat from step 1. 
                    - (5 shots per 0.25s + 4.49s)
                    - Instant DPS: 1 shot/0.05s
                    - Clip DPS: 5 shots/(0.05s*4) = 1 shot/0.04s
                    - Cycle DPS: 5 shots/(0.05s*4 + 4.49s) = 1 shot/0.94s
                - With infinite ammo:
                    1. Shoot instaneously
                    2. Wait for 0.05s (TimeBetweenShots)
                    3. Repeat from step 1 until BurstLength shots have been fired (5 shots total)
                    3.2 BurstLength shots have been fired: Wait 1.3s (TimeBetweenBursts)
                    4. Repeat from step 1. 
                    - (5 shots per 0.25s + 1.3s)
                    - Instant DPS: 1 shot/0.05s
                    - Clip DPS: 5 shots/(0.05s*4) = 1 shot/0.04s
                    - Cycle DPS: 5 shots/(0.05s*4 + 1.3s) = 1 shot/0.29s (note that this is the only metric that differs to without infinite ammo. Its also the only scenario where the 1.3s burst delay is used)

                
        - Misc notes:
            - There are currently no charge weapons with a NoShootingTime where damage is affected by how much it is charged
        """
        return
        # Total shot_damage per clip
        total_shot_damage = clip_size * shot_damage

        time_between_shots = 60 / rounds_per_per_minute

        # Time to fire entire clip (last shot doesn’t need extra delay)
        time_to_empty_clip = (clip_size - 1) * time_between_shots
        
        # InstantDPS (instantaneous, first shot at t=0)
        burst_dps = shot_damage / time_between_shots if time_between_shots > 0 else None
        if burst_dps is None:
            raise ValueError("Burst DPS calculation failed")

        # ClipDPS (shot_damage per time to empty clip)
        clip_dps = total_shot_damage * clip_size / time_to_empty_clip if time_to_empty_clip > 0 else None
        
        # CycleDPS (includes reload cycle)
        sustained_dps = total_shot_damage / (time_to_empty_clip + reload_time)

        res = {
            "InstantDPS": burst_dps,
        }

        if clip_dps is not None:
            res["ClipDPS"] = clip_dps

        res["CycleDPS"] = sustained_dps

        return res      


                    



                    

    # Calculate DPS
        # for shot_damage_key in shot_damage_keys:
        #     if not all(k in parsed_level for k in ['RoundsPerMinute', 'TimeToReload', 'ClipSize', shot_damage_key]):
        #         continue
        #     dps_stats = {
        #         'RoundsPerMinute': parsed_level.get('RoundsPerMinute'),
        #         'TimeToReload': parsed_level.get('TimeToReload'),
        #         'ClipSize': parsed_level.get('ClipSize'),
        #         'ShotDamage': parsed_level.get(shot_damage_key)
        #     }
        #     parsed_level[f"DPS_{shot_damage_key}"] = self.calculate_dps(
        #         dps_stats['RoundsPerMinute'],
        #         dps_stats['TimeToReload'],
        #         dps_stats['ClipSize'],
        #         dps_stats['ShotDamage']
        #     )
        #     log(f"Calculated DPS for {shot_damage_key}: {parsed_level[f'DPS_{shot_damage_key}']}")


    #################################
    #     Level Diffs/Upgrade Costs #
    #################################
    @staticmethod
    def get_level_diffs_per_module(module_class_objects):
        def extract_base_and_max(module):
            level_base = {}
            level_max = {}
            for level_category, level_data in module.levels.items():
                if level_category == 'scrap_rewards':
                    continue
                def add_category(data):
                    if not data or not data.get("variables"):
                        return
                    level_base.update(data["variables"][0])
                    level_max.update(data["variables"][-1])
                if isinstance(level_data, list):
                    for item in level_data:
                        add_category(item)
                elif isinstance(level_data, dict):
                    add_category(level_data)
            return level_base, level_max
        
        def calc_diff(val1, val2, module_id):
            if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
                raise TypeError(f"Invalid type for value in module {module_id}, val1 {val1} val2 {val2}")
            if val1 == 0 and val2 == 0:
                diff_value = 0 #no div by 0 necessary to deem this true
            elif val1 != 0:
                diff_value = (val2 - val1) / val1
            else:
                diff_value = f"+{val2:.1f}"
            if diff_value == 0:
                return None
            return diff_value
        
        def calculate_upgrade_costs(module, total_upgrade_costs):
            module_upgrade_costs = {}
            module_scalars = module.levels.get('module_scalars')
            if module_scalars is None:
                return None
            for level_index, level_data in enumerate(module_scalars['variables']):
                upgrade_cost = level_data.get('UpgradeCurrency')
                if not upgrade_cost:
                    log(f"Warning: No upgrade cost found for module {getattr(module, 'id', None)} at level {level_index+1}")
                    continue
                currency_id = upgrade_cost['currency_id']
                currency_amount = upgrade_cost['amount']
                module_upgrade_costs[currency_id] = module_upgrade_costs.get(currency_id, 0) + currency_amount
                total_upgrade_costs[currency_id] = total_upgrade_costs.get(currency_id, 0) + currency_amount
            return module_upgrade_costs

        total_upgrade_costs = {}
        distinct_stat_keys = set()
        level_diffs = {}

        def register_distinct_stat(stat):
            if stat is not None and stat not in distinct_stat_keys:
                distinct_stat_keys.add(stat)

        superficial_keys = {
            'Health', 'Level', 'Def', 'Atk', 'Mob', 'AbilityPower', 'Mobility',
            'ModuleClass_1', 'ModuleClass_2', 'ModuleTag_1', 'ModuleTag_2',
            'ModuleFaction', 'FirePower', 'bIsPerk'
        }

        for module_id, module in module_class_objects.items():
            if getattr(module, 'production_status', None) != 'Ready':
                continue
            log(f"Analyzing level differences for module: {module_id}")
            level_base, level_max = extract_base_and_max(module)
            diff = {}

            def add_diff(key, value):
                if value is not None:
                    diff[key] = value
                    register_distinct_stat(key)

            for key in level_base.keys():
                if key in superficial_keys or key in {'ScrapRewards', 'UpgradeCurrency'}:
                    continue
                elif key in ['DPS_DamageArmor', 'DPS_DamageNoArmor', 'DPS_AoeArmor', 'DPS_AoeNoArmor']:
                    dps_keys = level_base[key] #InstantDPS, ClipDPS, CycleDPS
                    for dps_key in dps_keys:
                        add_diff(f"{key}_{dps_key}", calc_diff(level_base[key][dps_key], level_max[key][dps_key], module_id))
                else:
                    add_diff(key, calc_diff(level_base[key], level_max[key], module_id))

            module_upgrade_costs = calculate_upgrade_costs(module, total_upgrade_costs)
            level_diffs[module_id] = {
                'stats_percent_increase': dict(sorted(diff.items()))
            }
            if module_upgrade_costs:
                level_diffs[module_id]['total_upgrade_cost'] = module_upgrade_costs

        return {
            'level_diffs': level_diffs,
            'distinct_stat_keys': distinct_stat_keys,
            'total_upgrade_costs': total_upgrade_costs
        }

    @staticmethod
    def get_ranks_per_stat(level_diffs_by_module, module_stat_objects, distinct_stat_keys):
        stat_keys_to_not_rank = {'PrimaryParameter', 'SecondaryParameter'}
        stat_keys_to_rank = [key for key in distinct_stat_keys if key not in stat_keys_to_not_rank]

        def get_more_is_better_map(stat_keys_to_rank, module_stat_objects):
            # if stat_key is not in map.keys(); search by ModuleStat.short_key
            # if stat_key is in map, use it as:
            # {stat_key: module_stat_id: str or <more_is_better>: bool}
            stat_to_more_is_better = {
                "ChargeDuration": "DA_ModuleStat_ChargeDrain.0",
                "Cooldown": "DA_ModuleStat_Cooldown.0",
                "ShieldRegeneration": "DA_ModuleStat_ShieldRegeneration.0",
                "TimeToReload": "DA_ModuleStat_ReloadingTime.0",
                "DamageArmor": "DA_ModuleStat_ArmorDamage.0",
                "AoeArmor": True,
                "RoundsPerMinute": "DA_ModuleStat_FireRate.0",
                "FuelCapacity": "DA_ModuleStat_FuelCapacity.0",
                "ShieldAmount": "DA_ModuleStat_ShieldAmount.0",
                "ShieldDelayReduction": "DA_ModuleStat_ShieldDelayReduction.0",
                "AoeNoArmor": True,
                "Armor": "DA_ModuleStat_Armor.0",
                "TimeBetweenShots": True,
                "DamageNoArmor": "DA_ModuleStat_ShieldDamage.0",
                "DPS_DamageArmor_InstantDPS": True,
                "DPS_DamageArmor_ClipDPS": True,
                "DPS_DamageArmor_CycleDPS": True,
                "DPS_DamageNoArmor_InstantDPS": True,
                "DPS_DamageNoArmor_ClipDPS": True,
                "DPS_DamageNoArmor_CycleDPS": True,
                "DPS_AoeArmor_InstantDPS": True,
                "DPS_AoeArmor_ClipDPS": True,
                "DPS_AoeArmor_CycleDPS": True,
                "DPS_AoeNoArmor_InstantDPS": True,
                "DPS_AoeNoArmor_ClipDPS": True,
                "DPS_AoeNoArmor_CycleDPS": True
            }
            stat_to_more_is_better_final = {}
            for stat_key in stat_keys_to_rank:
                entry = stat_to_more_is_better.get(stat_key)
                if entry is None:
                    module_stat = next((stat for stat in module_stat_objects.values() if stat.short_key == stat_key), None)
                    if module_stat is None:
                        raise ValueError(f"Unknown module stat for short_key {stat_key}")
                    more_is_better = getattr(module_stat, 'more_is_better', True)
                elif isinstance(entry, str):
                    module_stat = module_stat_objects[entry]
                    more_is_better = getattr(module_stat, 'more_is_better', True)
                elif isinstance(entry, bool):
                    more_is_better = entry
                else:
                    raise ValueError(f"Unknown more_is_better entry for stat {stat_key}: {entry}")
                stat_to_more_is_better_final[stat_key] = more_is_better
            return stat_to_more_is_better_final
        stat_to_more_is_better = get_more_is_better_map(stat_keys_to_rank, module_stat_objects)

        def rank_stats(level_diffs_by_module, stat_keys_to_rank, stat_to_more_is_better):
            stat_ranks = {key: {} for key in stat_keys_to_rank}
            for stat_key in stat_ranks:
                module_increases = []
                for module_id, module_diff_data in level_diffs_by_module.items():
                    percent_increase = module_diff_data['stats_percent_increase'].get(stat_key)
                    if percent_increase is not None:
                        module_increases.append((module_id, percent_increase))
                should_reverse = not stat_to_more_is_better[stat_key]
                module_increases.sort(key=lambda x: (float('-inf') if isinstance(x[1], str) else x[1]), reverse=should_reverse)
                for rank, (module_id, _) in enumerate(module_increases[::-1]):
                    stat_ranks[stat_key][module_id] = rank
            return stat_ranks
        return rank_stats(level_diffs_by_module, stat_keys_to_rank, stat_to_more_is_better)

    @staticmethod
    def get_ranks_per_module(stat_ranks, module_ids: list):
        per_module_ranks = {}
        for module_id in module_ids:
            my_module_ranks = {
                stat: stat_ranks[stat].get(module_id, 0) / len(stat_ranks[stat]) if stat in stat_ranks and len(stat_ranks[stat]) > 0 else 0
                for stat in stat_ranks if module_id in stat_ranks[stat]
            }
            per_module_ranks[module_id] = dict(sorted(my_module_ranks.items()))
        return per_module_ranks

    @staticmethod
    def get_level_diffs_per_stat(level_diffs_by_module, stat_ranks):
        verbose_stat_ranks = {
            stat_key: {
                module_id: level_diffs_by_module[module_id]['stats_percent_increase'][stat_key]
                for module_id in stat_rank
            }
            for stat_key, stat_rank in stat_ranks.items()
        }
        return verbose_stat_ranks

    ##########################
    #          Other         #
    ##########################

    def to_json(self):
        """Return analysis data as pretty-printed JSON."""
        data = {
            'level_diffs_by_module': self.level_diffs_by_module,
            'level_diffs_by_stat': self.level_diffs_by_stat,
            'total_upgrade_cost_for_all_modules': self.total_upgrade_cost_for_all_modules
        }
        return json.dumps(data, ensure_ascii=False, indent=4)

    def to_file(self):
        """Write analysis data to output file."""
        file_path = os.path.join(PARAMS.output_path, f'{self.__class__.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

def analyze(module_class, character_module_class, module_stat_class):
    analysis = Analysis(module_class, character_module_class, module_stat_class)
    analysis.to_file()