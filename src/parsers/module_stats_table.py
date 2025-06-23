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
        stats = props["AllModuleStats"]
        self.stats = dict()
        for stat_key, stat_data in stats:
            asset_path = stat_data["ObjectPath"]
            stat_id = ModuleStat.get_from_asset_path(asset_path)
            self.stats[stat_key] = stat_id