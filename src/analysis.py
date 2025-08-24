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
        level_diffs = {}
        for module_id, module in self.module_class.objects.items():
            log(f"Analyzing level differences for module: {module_id}")
            level_diffs[module_id] = {}
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
            superficial_keys = ['Level', 'Def', 'Atk', 'Mob', 'AbilityPower', 'Mobility', 'ModuleClass_1', 'ModuleClass_2', 'ModuleTag_1', 'ModuleTag_2', 'ModuleFaction', 'FirePower', 'bIsPerk']
            
            diffs = {}
            for key in level_base.keys():
                if key in superficial_keys:
                    continue
                elif key in ['ScrapRewards', 'UpgradeCurrency']: #not superficial but not worth gathering; upgrade currency gathered after
                    continue
                else:
                    base_value = level_base[key]
                    max_value = level_max[key]
                    diffs[key] = calc_diff(base_value, max_value)

                level_diffs[module_id] = diffs

        self.level_diffs = level_diffs

    def to_json(self):
        data = {}
        data['level_diffs'] = self.level_diffs
        return json.dumps(data, ensure_ascii=False, indent=4)

    def to_file(self):
        file_path = os.path.join(PARAMS.output_path, f'{self.__class__.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

def analyze(module_class):
    analysis = Analysis(module_class)
    analysis.to_file()