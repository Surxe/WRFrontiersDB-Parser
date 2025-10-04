# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object
from parsers.module_stat import ModuleStat

class ModuleStatsTable(Object):
    objects = dict()  # Dictionary to hold all ModuleStat instances
    
    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "AllModuleStats": (self._p_all_module_stats, "stats_ids"),
        }

        self._process_key_to_parser_function(key_to_parser_function, props)


    def _p_all_module_stats(self, data):
        parsed_stats = dict()
        for stat_key, stat_data in data.items():
            asset_path = stat_data["ObjectPath"]
            stat_id = ModuleStat.get_from_asset_path(asset_path)
            parsed_stats[stat_key] = stat_id
        
        return parsed_stats