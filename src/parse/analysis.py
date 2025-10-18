import sys
import os
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import OPTIONS, sort_dict
from loguru import logger
from typing import Literal

class Analysis:
    def __init__(self, module_class, module_stat_class, upgrade_cost_class, scrap_reward_class):
        self.module_class = module_class
        self.module_stat_class = module_stat_class
        self.upgrade_cost_class = upgrade_cost_class
        self.scrap_reward_class = scrap_reward_class

        # Level Diffs per module
        res = self.get_level_diffs_per_module(self.module_class.objects)
        self.level_diffs_by_module = res['level_diffs']
        distinct_stat_keys = res['distinct_stat_keys']

        # Level Diffs per stat
        stat_ranks = self.get_ranks_per_stat(self.level_diffs_by_module, self.module_stat_class.objects, distinct_stat_keys)
        ranks_per_module = self.get_ranks_per_module(stat_ranks, module_ids=self.level_diffs_by_module.keys())
        for module_id, rank in ranks_per_module.items():
            self.level_diffs_by_module[module_id]['stats_percentile'] = rank
        self.level_diffs_by_stat = self.get_level_diffs_per_stat(self.level_diffs_by_module, stat_ranks)

        # Upgrade cost & Scrap reward
        self.standard_cost_and_scrap = self.determine_standard_cost_and_scrap(
            self.module_class.objects,
            self.upgrade_cost_class.objects,
            self.scrap_reward_class.objects
        )

    ####################################################
    #      Level Diffs, per module and per stat        #
    ####################################################
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
            logger.debug(f"Analyzing level differences for module: {module_id}")
            level_base, level_max = extract_base_and_max(module)
            diff = {}

            def add_diff(key, value):
                if value is not None:
                    diff[key] = value
                    register_distinct_stat(key)

            for key in level_base.keys():
                logger.debug(f"Calculating diff for key: {key} in module: {module_id}")
                if key in superficial_keys or key in {'scrap_rewards_ids', 'upgrade_cost_id'}:
                    continue
                else:
                    add_diff(key, calc_diff(level_base[key], level_max[key], module_id))

            
            level_diffs[module_id] = {
                'stats_percent_increase': dict(sorted(diff.items()))
            }

        return {
            'level_diffs': level_diffs,
            'distinct_stat_keys': distinct_stat_keys
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
            }
            stat_to_more_is_better_final = {}
            for stat_key in stat_keys_to_rank:
                entry = stat_to_more_is_better.get(stat_key)
                if entry is None:
                    module_stat = next((stat for stat in module_stat_objects.values() if stat.short_key == stat_key), None)
                    if module_stat is None:
                        if stat_key.startswith('DPS_'): #dps stats are all more is better
                            more_is_better = True
                        else:
                            raise ValueError(f"stat_key: {stat_key}, Unknown module stat with this short_key")
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
                should_reverse = not stat_to_more_is_better.get(stat_key, None)
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
    
    ########################################
    #      Upgrade Cost & Scrap Reward     #
    ########################################
    @staticmethod
    def determine_standard_cost_and_scrap(module_class_objects, 
                                         upgrade_cost_class_objects, 
                                         scrap_reward_class_objects):
        """
        For each module rarity & level & currency_id, determine the most frequent upgrade cost
        Assign that upgrade cost as the standard upgrade cost for that module rarity & level & currency_id

        Returns:
            {
                <module_rarity>: {
                    <level>: {
                        <currency_id>: {
                            'upgrade_cost': <amount>,
                            'scrap_rewards': <amount>,
                        }
                    }
                }
            }
        """

        # First, determine the highest frequency
        """
        {
            <module_rarity_id>: {
                <level>: {
                    <currency_id>: {
                        'upgrade_cost': {
                            <upgrade_cost_amount>: count,
                        },
                        'scrap_reward': {
                            <scrap_reward_amount>: count,
                        }
                    }
                }
            }
        }
        """
        def get_frequency_map():
            frequency_map = {}
            for module_id, module in module_class_objects.items():
                logger.debug(f"Analyzing upgrade costs for module: {module_id}")

                # Get module scalars
                module_scalars = module.levels.get('module_scalars')
                if module_scalars is None:
                    continue

                # Ensure module rarity is added
                module_rarity_id = module.module_rarity_id
                if module_rarity_id not in frequency_map:
                    frequency_map[module_rarity_id] = {}

                # Iterate levels
                for level_index, level_data in enumerate(module_scalars['variables']):
                    level = level_index + 1
                    # Ensure level is added
                    if level not in frequency_map[module_rarity_id]:
                        frequency_map[module_rarity_id][level] = {}
                    
                    def register_amount(_type: Literal['scrap_reward', 'upgrade_cost'], level, currency_id, amount):
                        if currency_id not in frequency_map[module_rarity_id][level]:
                            frequency_map[module_rarity_id][level][currency_id] = {}
                        if _type not in frequency_map[module_rarity_id][level][currency_id]:
                            frequency_map[module_rarity_id][level][currency_id][_type] = {}
                        if amount not in frequency_map[module_rarity_id][level][currency_id][_type]:
                            frequency_map[module_rarity_id][level][currency_id][_type][amount] = 0
                        frequency_map[module_rarity_id][level][currency_id][_type][amount] += 1

                    # Register each scrap reward
                    scrap_rewards_ids = level_data.get('scrap_rewards_ids', [None])
                    for scrap_reward_id in scrap_rewards_ids:
                        scrap_reward = scrap_reward_class_objects.get(scrap_reward_id)
                        if scrap_reward is None:
                            continue
                        register_amount('scrap_reward', 
                                        level, 
                                        scrap_reward.currency_id, 
                                        scrap_reward.amount
                                        )
                    
                    # Register upgrade cost
                    upgrade_cost_id = level_data.get('upgrade_cost_id')
                    if upgrade_cost_id is None:
                        continue
                    upgrade_cost = upgrade_cost_class_objects[upgrade_cost_id]
                    currency_id = upgrade_cost.currency_id
                    currency_amount = upgrade_cost.amount
                    register_amount('upgrade_cost', level, currency_id, currency_amount)

            return frequency_map
        frequency_map = get_frequency_map()

        # Next, determine the most frequent upgrade cost & scrap reward
        standard_cost_and_scrap = {}
        for module_rarity_id, levels_data in frequency_map.items():
            if module_rarity_id not in standard_cost_and_scrap:
                standard_cost_and_scrap[module_rarity_id] = {}
            for level, currency_data in levels_data.items():
                if level not in standard_cost_and_scrap[module_rarity_id]:
                    standard_cost_and_scrap[module_rarity_id][level] = {}
                for currency_id, type_data in currency_data.items():
                    if currency_id not in standard_cost_and_scrap[module_rarity_id][level]:
                        standard_cost_and_scrap[module_rarity_id][level][currency_id] = {}
                    # Determine most frequent upgrade cost
                    upgrade_costs_freq = type_data.get('upgrade_cost', {})
                    if upgrade_costs_freq:
                        most_frequent_upgrade_cost = max(upgrade_costs_freq.items(), key=lambda x: x[1])[0]
                        standard_cost_and_scrap[module_rarity_id][level][currency_id]['upgrade_cost'] = most_frequent_upgrade_cost
                    # Determine most frequent scrap reward
                    scrap_rewards_freq = type_data.get('scrap_reward', {})
                    if scrap_rewards_freq:
                        most_frequent_scrap_reward = max(scrap_rewards_freq.items(), key=lambda x: x[1])[0]
                        standard_cost_and_scrap[module_rarity_id][level][currency_id]['scrap_reward'] = most_frequent_scrap_reward

        return standard_cost_and_scrap


    ##########################
    #          Other         #
    ##########################

    def to_json(self):
        """Return analysis data as pretty-printed JSON."""
        data = round_dict_values({
            'level_diffs_by_module': sort_dict(self.level_diffs_by_module, 1),
            'level_diffs_by_stat': sort_dict(self.level_diffs_by_stat, 1),
            'standard_cost_and_scrap': self.standard_cost_and_scrap
        })
        return json.dumps(data, ensure_ascii=False, indent=4)

    def to_file(self):
        """Write analysis data to output file."""
        file_path = os.path.join(OPTIONS.output_dir, f'{self.__class__.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

def round_dict_values(d):
    if isinstance(d, dict):
        return {k: round_dict_values(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [round_dict_values(item) for item in d]
    else:
        return round_val(d)

def round_val(value):
    if isinstance(value, str):
        return value
    return round(value, 5) #decimal places

def analyze(module_class, module_stat_class, upgrade_cost_class, scrap_reward_class):
    analysis = Analysis(module_class, module_stat_class, upgrade_cost_class, scrap_reward_class)
    analysis.to_file()