import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.module_stat import ModuleStat
from parsers.module_stats_table import ModuleStatsTable
from parsers.stat_maps import STAT_KEY_TO_MODULE_STAT_ID, SYNTHETIC_STAT_MORE_IS_BETTER
from loguru import logger

class Stat(ParseObject):
    objects = dict()  # Dict to hold all Stat instances keyed by short_key ID

    def _parse(self):
        # Stat instances are constructed programmatically during enrichment
        pass

    @classmethod
    def generate_all(cls):
        """
        Enrichment generator that creates Stat objects and synthetic ModuleStats for all distinct_stat_keys.
        """
        distinct_stat_keys = set()
        superficial_keys = {
            'Health', 'Level', 'Def', 'Atk', 'Mob', 'AbilityPower',
            'ModuleClass_1', 'ModuleClass_2', 'ModuleTag_1', 'ModuleTag_2',
            'ModuleFaction', 'FirePower', 'bIsPerk',
            'ArmorDPS', 'ShieldDPS', 'scrap_rewards_refs', 'upgrade_cost_ref',
            'PrimaryParameter', 'SecondaryParameter'
        }

        from parsers.module import Module
        for module in Module.objects.values():
            if getattr(module, 'production_status', None) != 'Ready':
                continue
            
            level_data_attrs = ['module_scalars', 'abilities_scalars']
            for attr in level_data_attrs:
                attr_data = getattr(module, attr, None)
                if attr_data is None:
                    continue
                
                # Handle lists of scalars (abilities_scalars) or a single dict (module_scalars)
                items = attr_data if isinstance(attr_data, list) else [attr_data]
                for item in items:
                    if not isinstance(item, dict) or 'levels' not in item:
                        continue
                    levels_info = item['levels']
                    if 'variables' in levels_info and levels_info['variables']:
                        for key in levels_info['variables'][0].keys():
                            if key not in superficial_keys:
                                distinct_stat_keys.add(key)
                    # Constants are stats too (WeightDrain, LoadCapacity, ...); their
                    # string metadata (ID, Rarity) is not
                    for key, value in levels_info.get('constants', {}).items():
                        if key not in superficial_keys and _is_number(value):
                            distinct_stat_keys.add(key)
        
        for stat_key in distinct_stat_keys:
            if stat_key in cls.objects:
                continue

            target_module_stat = None

            # Path A: Explicit manual mapping to an existing ModuleStat ID
            mapped_stat_id = STAT_KEY_TO_MODULE_STAT_ID.get(stat_key)
            if mapped_stat_id is not None:
                target_module_stat = ModuleStat.get_from_id(mapped_stat_id)
                if target_module_stat is None:
                    raise ValueError(
                        f"Stat key '{stat_key}' maps to ModuleStat ID '{mapped_stat_id}' in STAT_KEY_TO_MODULE_STAT_ID, "
                        f"but no ModuleStat with ID '{mapped_stat_id}' exists."
                    )

            # Path B: the game's own scalar key -> ModuleStat map (ModuleStatsTable)
            if target_module_stat is None:
                target_module_stat = _module_stat_from_stats_tables(stat_key)

            # Path C: 1-to-1 short_key match against existing ModuleStats
            if target_module_stat is None:
                target_module_stat = next(
                    (ms for ms in ModuleStat.objects.values() if getattr(ms, 'short_key', None) == stat_key),
                    None
                )

            # Path D: Dynamic DPS prefix check (or synthetic lookup)
            if target_module_stat is None and stat_key.startswith('DPS_'):
                synthetic_id = f"DA_ModuleStat_Synthetic_{stat_key}"
                target_module_stat = ModuleStat.get_from_id(synthetic_id)
                if target_module_stat is None:
                    target_module_stat = ModuleStat(synthetic_id, source_data={"Properties": {}})
                    target_module_stat.short_key = stat_key
                    target_module_stat.more_is_better = True

            # Path E: Synthetic ModuleStat creation via SYNTHETIC_STAT_MORE_IS_BETTER
            if target_module_stat is None:
                if stat_key in SYNTHETIC_STAT_MORE_IS_BETTER:
                    synthetic_id = f"DA_ModuleStat_Synthetic_{stat_key}"
                    more_is_better_val = SYNTHETIC_STAT_MORE_IS_BETTER[stat_key]
                    target_module_stat = ModuleStat(synthetic_id, source_data={"Properties": {}})
                    target_module_stat.short_key = stat_key
                    target_module_stat.more_is_better = more_is_better_val
                else:
                    # Developer Notification Error
                    raise ValueError(
                        f"Newly added stat short_key '{stat_key}' does not have a 1-to-1 ModuleStat match.\n"
                        f"- If '{stat_key}' relates to an existing ModuleStat, map its ID in STAT_KEY_TO_MODULE_STAT_ID in 'stat_maps.py'.\n"
                        f"- If '{stat_key}' does NOT relate to an existing ModuleStat, define its 'more_is_better' (True/False) entry in SYNTHETIC_STAT_MORE_IS_BETTER in 'stat_maps.py'."
                    )

            # Create the Stat ParseObject
            stat_obj = cls(id=stat_key, source_data={})
            stat_obj.module_stat_ref = target_module_stat.to_ref()


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _module_stat_from_stats_tables(stat_key: str):
    """The ModuleStat the ModuleStatsTables map stat_key to, or None. Logs an error if
    the tables disagree."""
    refs = {table.stats_refs[stat_key] for table in ModuleStatsTable.objects.values()
            if stat_key in getattr(table, 'stats_refs', {})}
    if len(refs) > 1:
        logger.error(f"Stat key '{stat_key}' maps to different ModuleStats across ModuleStatsTables: {refs}")
        return None
    return ModuleStat.get_from_ref(refs.pop()) if refs else None
