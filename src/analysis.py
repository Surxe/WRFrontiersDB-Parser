import sys
import os
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, PARAMS


class Analysis:

    def __init__(self, module_class, module_stat_class):
        self.module_class = module_class
        self.module_stat_class = module_stat_class

        res = self.get_level_diffs_per_module(self.module_class.objects)
        self.level_diffs_by_module = res['level_diffs']
        distinct_stat_keys = res['distinct_stat_keys']
        self.total_upgrade_cost_for_all_modules = res['total_upgrade_costs']

        stat_ranks = self.get_ranks_per_stat(self.level_diffs_by_module, self.module_stat_class.objects, distinct_stat_keys)

        ranks_per_module = self.get_ranks_per_module(stat_ranks, module_ids=self.level_diffs_by_module.keys())
        for module_id, rank in ranks_per_module.items():
            self.level_diffs_by_module[module_id]['stats_percentile'] = rank

        self.level_diffs_by_stat = self.get_level_diffs_per_stat(self.level_diffs_by_module, stat_ranks)

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
    #           DPS          #
    ##########################

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

def analyze(module_class, module_stat_class):
    analysis = Analysis(module_class, module_stat_class)
    analysis.to_file()