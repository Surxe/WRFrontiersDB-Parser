# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, PARAMS

import json

class Analysis:
    def __init__(self, module_class):
        self.module_class = module_class
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

        # For each stat, assign a rank to each module based on its percent increase. Worst = top 100% (1), best = top 0% (0)
        stat_ranks = {key: {} for key in distinct_stat_keys}
        stat_keys_to_not_rank = ['PrimaryParameter', 'SecondaryParameter'] #what these affect vary a lot per robot, not really rankable
        for stat_key in distinct_stat_keys:
            if stat_key in stat_keys_to_not_rank:
                continue
            # Gather all modules with this stat and their percent increases
            module_increases = []
            for module_id, module_diff_data in self.level_diffs_by_module.items():
                percent_increase = module_diff_data['stats_percent_increase'].get(stat_key)
                if percent_increase is not None:
                    module_increases.append((module_id, percent_increase))
            # Sort modules by percent increase (descending, best first)
            module_increases.sort(key=lambda x: (float('-inf') if isinstance(x[1], str) else x[1]), reverse=False)
            # Assign ranks: highest gets len-1, lowest gets 0
            for rank, (module_id, _) in enumerate(module_increases[::-1]):
                stat_ranks[stat_key][module_id] = rank
        # Store ranks in each module's diff data
        for module_id, module_diff_data in self.level_diffs_by_module.items():
            module_stat_ranks = {stat: stat_ranks[stat].get(module_id)/len(stat_ranks[stat]) if stat in stat_ranks and len(stat_ranks[stat]) > 0 else 0 for stat in distinct_stat_keys if module_id in stat_ranks[stat]}
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

def analyze(module_class):
    analysis = Analysis(module_class)
    analysis.to_file()