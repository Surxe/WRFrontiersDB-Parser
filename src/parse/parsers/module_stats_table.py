# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.module_stat import ModuleStat

class ModuleStatsTable(ParseObject):
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
            stat_id = ModuleStat.create_from_asset(stat_data).to_ref()
            parsed_stats[stat_key] = stat_id
        
        return parsed_stats