import sys
import os
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import OPTIONS, sort_dict
from loguru import logger
from typing import Literal

class Analysis:
    def __init__(self, module_class, module_stat_class, upgrade_cost_class, scrap_reward_class, factory_preset_class):
        self.module_class_objects = module_class.objects
        self.module_stat_class_objects = module_stat_class.objects
        self.upgrade_cost_class_objects = upgrade_cost_class.objects
        self.scrap_reward_class_objects = scrap_reward_class.objects
        self.factory_preset_class_objects = factory_preset_class.objects

        # Upgrade cost & Scrap reward
        self.frequency_map = self.get_frequency_map()
        self.standard_cost_and_scrap = self.determine_standard_cost_and_scrap(self.frequency_map)

        # Level Diffs per module
        res = self.get_level_diffs_per_module()
        self.level_diffs_by_module = res['level_diffs']
        distinct_stat_keys = res['distinct_stat_keys']

        # Ranking of diffs per module, level diff per stat
        stat_ranks = self.get_ranks_per_stat(self.level_diffs_by_module, distinct_stat_keys)
        ranks_per_module = self.get_ranks_per_module(stat_ranks, module_ids=self.level_diffs_by_module.keys())
        for module_id, rank in ranks_per_module.items():
            self.level_diffs_by_module[module_id]['stats_percentile'] = rank
        self.level_diffs_by_stat = self.get_level_diffs_per_stat(self.level_diffs_by_module, stat_ranks)

        # Determine cost of each module
        self.modules_upgrade_costs = self.get_modules_upgrade_costs(self.standard_cost_and_scrap)
        # Add upgrade cost to lvl diff per module, but not the ranking
        self.level_diffs_by_module = self.add_upgrade_cost_to_level_diffs(self.level_diffs_by_module, self.modules_upgrade_costs)

        # Determine upgrade costs of each factory preset
        self.factory_preset_upgrade_costs = self.calculate_factory_preset_upgrade_costs(self.standard_cost_and_scrap)

        # Determine grand total upgrade costs of production only modules, and 2 of each shoulder rather than 1
        self.total_upgrade_costs = self.calculate_total_upgrade_costs(self.modules_upgrade_costs)

    ########################################
    #      Upgrade Cost & Scrap Reward     #
    ########################################
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
    def get_frequency_map(self):
        frequency_map = {}
        for module_id, module in self.module_class_objects.items():
            logger.debug(f"Analyzing upgrade costs for module: {module_id}")

            # Get module scalars
            module_scalars = getattr(module, 'module_scalars', None)
            if module_scalars is None:
                continue
            module_scalars = module_scalars.get("levels")
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
                    scrap_reward = self.scrap_reward_class_objects.get(scrap_reward_id)
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
                upgrade_cost = self.upgrade_cost_class_objects[upgrade_cost_id]
                currency_id = upgrade_cost.currency_id
                currency_amount = upgrade_cost.amount
                register_amount('upgrade_cost', level, currency_id, currency_amount)

        return frequency_map

    @staticmethod
    def determine_standard_cost_and_scrap(frequency_map):
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

        def get_most_freq_amount(amount_freq_map):
            """
            Args:
                amount_freq_map: {
                    <amount>: count,
                }

            Returns:
                most frequent amount (int)
            """
            biggest_entry = (None, -1)  # (amount, count)
            for amount_str, count in amount_freq_map.items():
                amount = int(amount_str)
                if count > biggest_entry[1]:
                    biggest_entry = (amount, count)
            if biggest_entry[1] <= 3:
                return 0 # if there are only outliers or too few data points it should be treated as 0 cost
            return biggest_entry[0]

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

                    # Determine most frequent scrap reward
                    scrap_rewards_freq = type_data.get('scrap_reward', {})
                    if scrap_rewards_freq:
                        most_frequent_scrap_reward = get_most_freq_amount(scrap_rewards_freq)
                        standard_cost_and_scrap[module_rarity_id][level][currency_id]['scrap_reward'] = most_frequent_scrap_reward
                    
                    # Determine most frequent upgrade cost
                    upgrade_costs_freq = type_data.get('upgrade_cost', {})
                    if upgrade_costs_freq:
                        most_frequent_upgrade_cost = get_most_freq_amount(upgrade_costs_freq)
                        standard_cost_and_scrap[module_rarity_id][level][currency_id]['upgrade_cost'] = most_frequent_upgrade_cost

        # Then, ensure upgrade_cost and scrap_reward in each entry, default to 0 otherwise
        for module_rarity_id, levels_data in standard_cost_and_scrap.items():
            for level, currency_data in levels_data.items():
                for currency_id, cost_and_scrap in currency_data.items():
                    if 'upgrade_cost' not in cost_and_scrap:
                        cost_and_scrap['upgrade_cost'] = 0
                    if 'scrap_reward' not in cost_and_scrap:
                        cost_and_scrap['scrap_reward'] = 0

        # Finally, sort each level's entry
        for module_rarity_id, levels_data in standard_cost_and_scrap.items():
            for level, currency_data in levels_data.items():
                standard_cost_and_scrap[module_rarity_id][level] = sort_dict(dict(currency_data.items()))

        return standard_cost_and_scrap
        

    ####################################################
    #      Level Diffs, per module and per stat        #
    ####################################################
    def get_level_diffs_per_module(self):
        def extract_base_and_max(module):
            level_base = {}
            level_max = {}

            # Extract level data from both attrs
            level_data_attrs = ['module_scalars', 'abilities_scalars']
            for attr in level_data_attrs:
                level_data = getattr(module, attr, None)
                if level_data is None:
                    continue
                if 'levels' not in level_data:
                    continue
                level_data = level_data['levels']

                # Add to level base and max for each one
                def add_category(data):
                    if not data or not data.get("variables"):
                        return
                    this_lvl_base = data["variables"][0]
                    this_lvl_max = data["variables"][-1]

                    def update_no_conflict(target_dict, source_dict):
                        for key, value in source_dict.items():
                            if key not in target_dict:
                                target_dict[key] = value
                            else:
                                if target_dict[key] != value:
                                    logger.error(f"Structure change: Conflict detected for module {module.id} key {key}: existing value {target_dict[key]}, new value {value}. Keeping existing value.")
                    update_no_conflict(level_base, this_lvl_base)
                    update_no_conflict(level_max, this_lvl_max)
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
            'ModuleFaction', 'FirePower', 'bIsPerk',
            'ArmorDPS', 'ShieldDPS' #for now. these are UI numbers and are often wrong. will do real dps calcs later.
        }

        for module_id, module in self.module_class_objects.items():
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

    def get_ranks_per_stat(self, level_diffs_by_module, distinct_stat_keys):
        stat_keys_to_not_rank = {'PrimaryParameter', 'SecondaryParameter'}
        stat_keys_to_rank = [key for key in distinct_stat_keys if key not in stat_keys_to_not_rank]

        def get_more_is_better_map(stat_keys_to_rank):
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
                    module_stat = next((stat for stat in self.module_stat_class_objects.values() if stat.short_key == stat_key), None)
                    if module_stat is None:
                        if stat_key.startswith('DPS_'): #dps stats are all more is better
                            more_is_better = True
                        else:
                            raise ValueError(f"stat_key: {stat_key}, Unknown module stat with this short_key")
                    more_is_better = getattr(module_stat, 'more_is_better', True)
                elif isinstance(entry, str):
                    module_stat = self.module_stat_class_objects[entry]
                    more_is_better = getattr(module_stat, 'more_is_better', True)
                elif isinstance(entry, bool):
                    more_is_better = entry
                else:
                    raise ValueError(f"Unknown more_is_better entry for stat {stat_key}: {entry}")
                stat_to_more_is_better_final[stat_key] = more_is_better
            return stat_to_more_is_better_final
        stat_to_more_is_better = get_more_is_better_map(stat_keys_to_rank)

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
    
    ############################
    #   Module Upgrade Costs   #
    ############################
    def get_module_upgrade_costs(self, module_id, standard_cost_and_scrap):
        """
        Returns:
            None if module is not production ready

            (<upgrade_costs_dict>, is_shoulder) where
            upgrade_costs_dict = {
                <currency_id>: <total_upgrade_cost_amount>,
            }
            
        """
        module_upgrade_costs = {}

        def get_upgrade_cost_from_standard(cost_scrap_data):
            """
            Args:
                cost_scrap_data = {
                    <currency_id>: {
                        'upgrade_cost': <amount>,
                        'scrap_reward': <amount>,
                    }
                }

            Returns:
                (<currency_id>, <upgrade_cost_amount>)

                None if no non-zero upgrade cost found or multiple non-zero upgrade costs found
            """

            found_nonzero_pairs = []
            for currency_id, cost_and_scrap in cost_scrap_data.items():
                upgrade_cost = cost_and_scrap.get('upgrade_cost', 0)
                if upgrade_cost > 0:
                    found_nonzero_pairs.append((currency_id, upgrade_cost))
            if len(found_nonzero_pairs) == 0:
                return None
            elif len(found_nonzero_pairs) == 1:
                return found_nonzero_pairs[0]
            else:
                logger.error(f"Structure change: multiple non-zero upgrade costs found: {found_nonzero_pairs}")
                return None
        
        logger.debug(f"Getting upgrade costs for module: {module_id}")
        module = self.module_class_objects[module_id]
        if getattr(module, 'production_status', None) != 'Ready':
            return None
        module_rarity_id = module.module_rarity_id
        is_shoulder = getattr(module, 'module_type_id', '') == 'DA_ModuleType_Shoulder.0'

        rarity_standard_cost_and_scrap = standard_cost_and_scrap[module_rarity_id]
        for level, cost_scrap_data in rarity_standard_cost_and_scrap.items():
            logger.debug(f"Adding upgrade cost for module: {module_id}, level: {level}")

            # use the most frequent upgrade cost for this module rarity & level, as opposed to whats in data
            upgrade_cost_pair = get_upgrade_cost_from_standard(cost_scrap_data)

            # add to total
            if upgrade_cost_pair is not None:
                currency_id, upgrade_cost_amount = upgrade_cost_pair
                if currency_id not in module_upgrade_costs:
                    module_upgrade_costs[currency_id] = 0
                module_upgrade_costs[currency_id] += upgrade_cost_amount

        return module_upgrade_costs, is_shoulder
    
    def get_modules_upgrade_costs(self, standard_cost_and_scrap):
        """
        Returns:
            {
                <module_id>: {
                    "is_shoulder": bool,
                    "upgrade_costs": {
                        <currency_id>: <total_upgrade_cost_amount>,
                    }
                }
            }
        """

        modules_upgrade_costs = {}
        for module_id in self.module_class_objects.keys():
            result = self.get_module_upgrade_costs(module_id, standard_cost_and_scrap)
            if result is None:
                continue
            upgrade_costs, is_shoulder = result
            modules_upgrade_costs[module_id] = {
                "is_shoulder": is_shoulder,
                "upgrade_costs": upgrade_costs
            }
        return modules_upgrade_costs

    def add_upgrade_cost_to_level_diffs(self, level_diffs_by_module, modules_upgrade_costs):
        """
        For each module, add non-zero upgrade cost to its level diffs
        """

        for module_id in level_diffs_by_module.keys():
            logger.debug(f"Adding upgrade cost to module: {module_id}")

            # add to level diffs
            this_module_upgrade = modules_upgrade_costs.get(module_id)
            if this_module_upgrade is None:
                continue
            this_module_upgrade_costs = this_module_upgrade["upgrade_costs"]
            for currency_id, upgrade_cost_amount in this_module_upgrade_costs.items():
                if 'total_upgrade_cost' not in level_diffs_by_module[module_id]:
                    level_diffs_by_module[module_id]['total_upgrade_cost'] = {}
                level_diffs_by_module[module_id]['total_upgrade_cost'][f'{currency_id}'] = upgrade_cost_amount

        return level_diffs_by_module
    
    ################################
    # Factory preset upgrade costs #
    ################################
    def calculate_factory_preset_upgrade_costs(self, standard_cost_and_scrap):
        """
        Returns:
            {
                <factory_preset_id>: {
                    <currency_id>: <total_upgrade_cost_amount>,
                }
            }
        """
        factory_preset_costs = {}
        for fpreset_id, fpreset in self.factory_preset_class_objects.items():
            for module_socket_name, module_data in fpreset.modules.items():
                module_id = module_data['id']
                this_module_upgrade_costs, _ = self.get_module_upgrade_costs(module_id, standard_cost_and_scrap)
                logger.debug(f"Adding upgrade cost for factory preset: {fpreset_id}")
            
                # For each currency_id, add to the fpreset's total
                for currency_id, upgrade_cost_amount in this_module_upgrade_costs.items():
                    if fpreset_id not in factory_preset_costs:
                        factory_preset_costs[fpreset_id] = {}
                    if currency_id not in factory_preset_costs[fpreset_id]:
                        factory_preset_costs[fpreset_id][currency_id] = 0
                    factory_preset_costs[fpreset_id][currency_id] += upgrade_cost_amount

        return factory_preset_costs
    

    ############################
    # Grand total upgrade cost #
    ############################
    def calculate_total_upgrade_costs(self, modules_upgrade_costs):
        total_upgrade_costs = {}  # <currency_id>: <total_upgrade_cost_amount>
        for module_id, module in self.module_class_objects.items():
            # Ensure its production ready module
            if getattr(module, 'production_status', None) != 'Ready':
                continue

            # Determine the non-zero upgrade cost for this module
            this_module_upgrade = modules_upgrade_costs[module_id]
            this_module_upgrade_costs = this_module_upgrade["upgrade_costs"]
            is_shoulder = this_module_upgrade["is_shoulder"]
            quantity = 2 if is_shoulder else 1

            # Add to grand total
            for currency_id, upgrade_cost_amount in this_module_upgrade_costs.items():
                if currency_id not in total_upgrade_costs:
                    total_upgrade_costs[currency_id] = 0
                total_upgrade_costs[currency_id] += upgrade_cost_amount * quantity

        return total_upgrade_costs


    ##########################
    #          Other         #
    ##########################
    def bundle_self(self):
        """Return self as one dictionary, keyed by the future file name."""
        return round_dict_values({
            'level_diffs_by_module': sort_dict(self.level_diffs_by_module, 1),
            'level_diffs_by_stat': sort_dict(self.level_diffs_by_stat, 1),
            'cost_scrap_frequency_map': self.frequency_map,
            'standard_cost_and_scrap': self.standard_cost_and_scrap,
            'total_upgrade_costs': self.total_upgrade_costs,
            'factory_preset_upgrade_costs': self.factory_preset_upgrade_costs,
        })

    def to_file(self):
        """Write analysis data to output file."""
        # Create Analysis folder if it doesn't exist
        analysis_dir = os.path.join(OPTIONS.output_dir, f'{self.__class__.__name__}')
        os.makedirs(analysis_dir, exist_ok=True)
        bundle = self.bundle_self()
        for file_name, data in bundle.items():
            file_path = os.path.join(analysis_dir, f'{file_name}.json')
            logger.debug(f"Writing analysis data to {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

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

def analyze(*classes):
    analysis = Analysis(*classes)
    analysis.to_file()