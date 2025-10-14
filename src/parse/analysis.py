import sys
import os
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import OPTIONS, sort_dict, logger

class Analysis:
    def __init__(self, module_class, module_stat_class, upgrade_cost_class):
        self.module_class = module_class
        self.module_stat_class = module_stat_class
        self.upgrade_cost_class = upgrade_cost_class
        self._analyze_level_differences()

    def _extract_base_and_max(self, module):
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

    def _calc_diff(self, val1, val2, module_id):
        if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
            raise TypeError(f"Invalid type for value in module {module_id}, val1 {val1} val2 {val2}")
        if val1 != 0:
            diff_value = (val2 - val1) / val1
        else:
            diff_value = f"+{val2:.1f}"
        if diff_value == 0:
            return None
        return diff_value

    def _calculate_upgrade_costs(self, module, total_upgrade_costs):
        module_upgrade_costs = {}
        module_scalars = module.levels.get('module_scalars')
        if module_scalars is None:
            return None
        for level_index, level_data in enumerate(module_scalars['variables']):
            upgrade_cost_id = level_data.get('upgrade_currency_id')
            if upgrade_cost_id is None:
                logger.debug(f"Warning: No upgrade cost ID found for module {getattr(module, 'id', None)} at level {level_index+1}")
                continue
            upgrade_cost = self.upgrade_cost_class.objects[upgrade_cost_id]
            currency_id = upgrade_cost.currency_id
            currency_amount = upgrade_cost.amount
            module_upgrade_costs[currency_id] = module_upgrade_costs.get(currency_id, 0) + currency_amount
            total_upgrade_costs[currency_id] = total_upgrade_costs.get(currency_id, 0) + currency_amount
        return module_upgrade_costs

    def _get_more_is_better_map(self, stat_keys_to_rank):
        """
        key is stat
        if value is bool, it indicates more_is_better directly
        if value is str, it indicates module_stat key to lookup more_is_better
        if for any key not in the map, it assumes key is a short_key of a stat to lookup more_is_better
        """
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
            "PrimaryParameter": True,
            "SecondaryParameter": True,
        }
        stat_to_more_is_better_final = {}
        for stat_key in stat_keys_to_rank:
            entry = stat_to_more_is_better.get(stat_key)
            if entry is None:
                module_stat = next((stat for stat in self.module_stat_class.objects.values() if stat.short_key == stat_key), None)
                if module_stat is None:
                    more_is_better = True #default to true
                    logger.error(f"No module stat found for short_key {stat_key}, defaulting more_is_better to True")
                more_is_better = getattr(module_stat, 'more_is_better', True)
            elif isinstance(entry, str):
                module_stat = self.module_stat_class.objects[entry]
                more_is_better = getattr(module_stat, 'more_is_better', True)
            elif isinstance(entry, bool):
                more_is_better = entry
            else:
                raise ValueError(f"Unknown more_is_better entry for stat {stat_key}: {entry}")
            stat_to_more_is_better_final[stat_key] = more_is_better
        return stat_to_more_is_better_final

    def _rank_modules(self, stat_keys_to_rank, stat_to_more_is_better):
        stat_ranks = {key: {} for key in stat_keys_to_rank}
        for stat_key in stat_ranks:
            module_increases = []
            for module_id, module_diff_data in self.level_diffs_by_module.items():
                percent_increase = module_diff_data['stats_percent_increase'].get(stat_key)
                if percent_increase is not None:
                    module_increases.append((module_id, percent_increase))
            should_reverse = not stat_to_more_is_better[stat_key]
            module_increases.sort(key=lambda x: (float('-inf') if isinstance(x[1], str) else x[1]), reverse=should_reverse)
            for rank, (module_id, _) in enumerate(module_increases[::-1]):
                stat_ranks[stat_key][module_id] = rank
        return stat_ranks

    def _build_verbose_stat_ranks(self, stat_ranks):
        verbose_stat_ranks = {
            stat_key: {
                module_id: self.level_diffs_by_module[module_id]['stats_percent_increase'][stat_key]
                for module_id in stat_rank
            }
            for stat_key, stat_rank in stat_ranks.items()
        }
        return verbose_stat_ranks

    def _analyze_level_differences(self):
        total_upgrade_costs = {}
        distinct_stat_keys = set()
        level_diffs = {}

        superficial_keys = {
            'ModuleClass_1', 'ModuleClass_2', 'ModuleTag_1', 'ModuleTag_2',
            'ModuleFaction', 'bIsPerk'
        }

        for module_id, module in self.module_class.objects.items():
            if getattr(module, 'production_status', None) != 'Ready':
                continue
            logger.debug(f"Analyzing level differences for module: {module_id}")
            level_base, level_max = self._extract_base_and_max(module)
            diff = {}
            for key in level_base.keys():
                if key in superficial_keys or key in ['ScrapRewards', 'upgrade_currency_id']:
                    continue
                base_value = level_base[key]
                max_value = level_max[key]
                diff[key] = self._calc_diff(base_value, max_value, module_id)
                if diff[key] is not None:
                    distinct_stat_keys.add(key)
            module_upgrade_costs = self._calculate_upgrade_costs(module, total_upgrade_costs)
            module_name = getattr(module, 'name', None)
            level_diffs[module_id] = {
                'stats_percent_increase': dict(sorted(diff.items()))
            }
            if module_upgrade_costs:
                level_diffs[module_id]['total_upgrade_cost'] = module_upgrade_costs
            if module_name is not None:
                level_diffs[module_id]['name'] = module_name

        self.level_diffs_by_module = level_diffs
        self.total_upgrade_cost_for_all_modules = total_upgrade_costs

        stat_keys_to_not_rank = {'PrimaryParameter', 'SecondaryParameter'}
        stat_keys_to_rank = [key for key in distinct_stat_keys if key not in stat_keys_to_not_rank]
        stat_to_more_is_better = self._get_more_is_better_map(stat_keys_to_rank)
        stat_ranks = self._rank_modules(stat_keys_to_rank, stat_to_more_is_better)

        for module_id, module_diff_data in self.level_diffs_by_module.items():
            module_stat_ranks = {
                stat: stat_ranks[stat].get(module_id, 0) / len(stat_ranks[stat]) if stat in stat_ranks and len(stat_ranks[stat]) > 0 else 0
                for stat in stat_ranks if module_id in stat_ranks[stat]
            }
            module_diff_data['stats_percentile'] = dict(sorted(module_stat_ranks.items()))

        self.level_diffs_by_stat = self._build_verbose_stat_ranks(stat_ranks)

    def to_json(self):
        """Return analysis data as pretty-printed JSON."""
        data = {
            'level_diffs_by_module': sort_dict(self.level_diffs_by_module, 1),
            'level_diffs_by_stat': sort_dict(self.level_diffs_by_stat, 1),
            'total_upgrade_cost_for_all_modules': sort_dict(self.total_upgrade_cost_for_all_modules, 1)
        }
        return json.dumps(data, ensure_ascii=False, indent=4)

    def to_file(self):
        """Write analysis data to output file."""
        file_path = os.path.join(OPTIONS.output_dir, f'{self.__class__.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

def analyze(module_class, module_stat_class, upgrade_cost_class):
    analysis = Analysis(module_class, module_stat_class, upgrade_cost_class)
    analysis.to_file()
