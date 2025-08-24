# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, PARAMS

import json

class Analysis:
    def __init__(self, module_class, module_stat_class):
        self.module_class = module_class
        self.module_stat_class = module_stat_class
        self.analysis_level_diff()

    def analysis_level_diff(self):
        # Extract %diff between lvl1 and lvl13, ignore diffs of 0
        distinct_stat_keys = set()
        level_diffs = {}
        for module_id, module in self.module_class.objects.items():
            if getattr(module, 'production_status', None) != 'Ready':
                continue
            log(f"Analyzing level differences for module: {module_id}")
            level_base = {}
            level_max = {}
            # Data can be in multiple categories like module_scalers{} or ability_scalers[{}]
            # Conglomerate base and max lvl for every attr in every category
            for level_category, level_data in module.levels.items():
                if level_category == 'scrap_rewards':
                    continue

                def add_category(level_data):
                    if level_data == [] or level_data is None or not level_data["variables"]:
                        return
                    level_base.update(level_data["variables"][0])
                    level_max.update(level_data["variables"][-1])
                if isinstance(level_data, list):
                    for item in level_data:
                        add_category(item)
                elif isinstance(level_data, dict):
                    add_category(level_data)
            
            # Calculate diff from base to max
            def calc_diff(val1, val2):
                if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
                    raise TypeError(f"Invalid type for value in module {module_id}, val1 {val1} val2 {val2}")

                diff_value = (val2 - val1) / val1 if val1 != 0 else f"+{val2:.1f}"

                if diff_value == 0:
                    return
                return diff_value
            
            # Ignore some superficial keys
            superficial_keys = ['Health', 'Level', 'Def', 'Atk', 'Mob', 'AbilityPower', 'Mobility', 'ModuleClass_1', 'ModuleClass_2', 'ModuleTag_1', 'ModuleTag_2', 'ModuleFaction', 'FirePower', 'bIsPerk']
            
            diff = {}
            for key in level_base.keys():
                if key in superficial_keys:
                    continue
                elif key in ['ScrapRewards', 'UpgradeCurrency']: #not superficial but not worth gathering; upgrade currency gathered after
                    continue
                
                base_value = level_base[key]
                max_value = level_max[key]
                diff[key] = calc_diff(base_value, max_value)
                if diff[key] is not None:
                    distinct_stat_keys.add(key)

            # Determine cumulative upgrade cost
            sum_costs = {}
            if module.levels['module_scalars'] is None:
                continue
            for level_index, level_data in enumerate(module.levels['module_scalars']['variables']):
                # Get the upgrade cost
                if 'UpgradeCurrency' not in level_data:
                    log(f"Warning: No upgrade cost found for module {module_id} at level {level_index+1}")
                    continue
                upgrade_cost = level_data['UpgradeCurrency']
                currency_id = upgrade_cost['currency_id']
                currency_amount = upgrade_cost['amount']

                # aggregate it
                if currency_id not in sum_costs:
                    sum_costs[currency_id] = 0
                sum_costs[currency_id] += currency_amount

            # Add all data to the record
            module_name = getattr(module, 'name', None)
            level_diffs[module_id] = {'stats_percent_increase': dict(sorted(diff.items()))}
            if sum_costs:
                level_diffs[module_id]['total_upgrade_cost'] = sum_costs
            if module_name is not None:
                level_diffs[module_id]['name'] = module_name

        self.level_diffs_by_module = level_diffs

        stat_keys_to_not_rank = ['PrimaryParameter', 'SecondaryParameter'] #what these affect vary a lot per robot, not really rankable
        stat_keys_to_rank = [distinct_stat_key for distinct_stat_key in distinct_stat_keys if distinct_stat_key not in stat_keys_to_not_rank]

        def get_more_is_better_map(self):
            # stat_key: <more_is_better> or <ModuleStat.more_is_better>
            stat_to_more_is_better = {
                "ChargeDuration": "DA_ModuleStat_ChargeDrain",
                "Cooldown": "DA_ModuleStat_Cooldown",
                "ShieldRegeneration": "DA_ModuleStat_ShieldRegeneration",
                "TimeToReload": "DA_ModuleStat_ReloadingTime",
                "DamageArmor": "DA_ModuleStat_ArmorDamage",
                "AoeArmor": True,
                "RoundsPerMinute": "DA_ModuleStat_FireRate",
                "FuelCapacity": "DA_ModuleStat_FuelCapacity",
                "ShieldAmount": "DA_ModuleStat_ShieldAmount",
                "ShieldDelayReduction": "DA_ModuleStat_ShieldDelayReduction",
                "AoeNoArmor": True,
                "Armor": "DA_ModuleStat_Armor",
                "TimeBetweenShots": True,
                "DamageNoArmor": "DA_ModuleStat_ShieldDamage",
                # all other stats are linked to ModuleStat by ModuleStat.short_key for more_is_better
            }

            # Create map stat_key: <more_is_better> from the above
            stat_to_more_is_better_final = {}
            for stat_key in stat_keys_to_rank:
                # Get mapped entry
                stat_to_more_is_better_entry = stat_to_more_is_better.get(stat_key)

                # Get the more_is_better value from it
                if stat_to_more_is_better_entry is None:
                    # find module stat by short_key
                    module_stat = next((stat for stat in self.module_stat_class.objects.values() if stat.short_key == stat_key), None) #mstat's more_is_better (found by short_key)
                    if module_stat is None:
                        raise ValueError(f"Unknown module stat for short_key {stat_key}")
                    more_is_better = getattr(module_stat, 'more_is_better', True)
                elif isinstance(stat_to_more_is_better_entry, str): #id of ModuleStat
                    module_stat = self.module_stat_class.objects[stat_to_more_is_better_entry] #modulestat's more_is_better
                    more_is_better = getattr(module_stat, 'more_is_better', True)
                elif isinstance(stat_to_more_is_better_entry, bool):
                    more_is_better = stat_to_more_is_better_entry
                else:
                    raise ValueError(f"Unknown more_is_better entry for stat {stat_key}: {stat_to_more_is_better_entry}")

                # Store the result in the final mapping
                stat_to_more_is_better_final[stat_key] = more_is_better
            
            return stat_to_more_is_better_final
        
        stat_to_more_is_better = get_more_is_better_map(self)
        print(f"stat_keys where more_is_better=False: {[stat_key for stat_key, more_is_better in stat_to_more_is_better.items() if not more_is_better]}") #curiousity

        # For each stat, assign a rank to each module based on its percent increase. Worst = top 100% (1), best = top 0% (0)
        stat_ranks = {key: {} for key in stat_keys_to_rank}
        for stat_key in stat_ranks.keys():
            # Gather all modules with this stat and their percent increases
            module_increases = []
            for module_id, module_diff_data in self.level_diffs_by_module.items():
                percent_increase = module_diff_data['stats_percent_increase'].get(stat_key)
                if percent_increase is not None:
                    module_increases.append((module_id, percent_increase))
            # Sort modules by percent increase (descending, best first)
            should_reverse = not stat_to_more_is_better[stat_key]
            module_increases.sort(key=lambda x: (float('-inf') if isinstance(x[1], str) else x[1]), reverse=should_reverse)
            # Assign ranks: highest gets len-1, lowest gets 0
            for rank, (module_id, _) in enumerate(module_increases[::-1]):
                stat_ranks[stat_key][module_id] = rank
        # Store ranks in each module's diff data
        for module_id, module_diff_data in self.level_diffs_by_module.items():
            module_stat_ranks = {stat: stat_ranks[stat].get(module_id)/len(stat_ranks[stat]) if stat in stat_ranks and len(stat_ranks[stat]) > 0 else 0 for stat in stat_ranks.keys() if module_id in stat_ranks[stat]}
            # Sort by key
            module_stat_ranks = dict(sorted(module_stat_ranks.items()))
            module_diff_data['stats_percentile'] = module_stat_ranks

        verbose_stat_ranks = {}
        for stat_key, stat_rank in stat_ranks.items():
            verbose_stat_ranks[stat_key] = {}
            for module_id, rank in stat_rank.items():
                verbose_stat_ranks[stat_key][module_id] = self.level_diffs_by_module[module_id]['stats_percent_increase'][stat_key]
        self.level_diffs_by_stat = verbose_stat_ranks

    def to_json(self):
        data = {}
        data['level_diffs_by_module'] = self.level_diffs_by_module
        data['level_diffs_by_stat'] = self.level_diffs_by_stat
        return json.dumps(data, ensure_ascii=False, indent=4)

    def to_file(self):
        file_path = os.path.join(PARAMS.output_path, f'{self.__class__.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

def analyze(module_class, module_stat_class):
    analysis = Analysis(module_class, module_stat_class)
    analysis.to_file()