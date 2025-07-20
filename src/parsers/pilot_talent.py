# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object, ParseAction, ParseTarget

from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path
from parsers.module_stat import ModuleStat
from parsers.module_tag import ModuleTag

from utils import asset_path_to_data, asset_path_to_file_path, get_json_data, parse_colon_colon

class PilotTalent(Object):
    objects = dict()  # Dictionary to hold all PilotTalent instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": (parse_localization, "name"),
            "Description": (parse_localization, "description"),
            "UIDescription": (parse_localization, "ui_description"),
            "ShortUIDescription": (parse_localization, "short_ui_description"),
            "Image": (parse_image_asset_path, "image_path"),
            "PilotTalent": (self._p_bp, None),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

    def _p_bp(self, data: dict):
        bp_file_path = asset_path_to_file_path(data["AssetPathName"])
        bp_data = get_json_data(bp_file_path)[0]
        if 'ClassDefaultObject' not in bp_data:
            return
        
        cdo_data = asset_path_to_data(bp_data["ClassDefaultObject"]["ObjectPath"])
        props = cdo_data["Properties"]

        key_to_parser_function = {
            "UberGraphFrame": None,
            "FadeOutTime": None, #pretty sure this is for the following OverlayMeshFx and not any gameplay effects
            "OverlayMeshFx": None,
            "Multiplier": None,
            "Effect": None,
            "TorsoFx": None,
            "VisualEffect": None,
            "SoundEffect": None,
            "Stream": None,
            "Trigger": None,
            "ActivationReaction": None,
            "OnActivateAkEvent": None,
            "OnDeactivateAkEvent": None,
            "bIsInfinity": None,
            
            # Save to default_properties with custom target names
            "Regen amount": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "DamageBoost": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "ArmorToRestore": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "AdditionalFuel": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "MaxStacks": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "TitanPoints": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "ChargeToAdd": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY
            },
            "Lifetime": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'default_properties',
                'target': ParseTarget.MATCH_KEY,
            },
            
            # Regular attributes
            "Stats": self._p_stats,
            "Buffs": self._p_buffs,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor=bp_file_path, tabs=2)

    def _p_stats(self, stats):
        parsed_stats = []
        for stat in stats:
            stat_id = ModuleStat.get_from_asset_path(stat["Key"].split('SModuleStatInfo\'')[1], log_tabs=1)
            value = stat["Value"]
            parsed_stats.append({
                "stat_id": stat_id,
                "value": value
            })

        if parsed_stats:
            return parsed_stats
        return None

    def _p_buffs(self, buffs: list):
        parsed_buffs = []
        
        for buff in buffs:
            parsed_buff = {}

            buff_asset_path = buff["ObjectPath"]
            buff_data = asset_path_to_data(buff_asset_path)
            buff_cdo_data = asset_path_to_data(buff_data["ClassDefaultObject"]["ObjectPath"])
            buff_props = buff_cdo_data["Properties"]

            weapon_selectors = []
            if 'WeaponSelectors' in buff_props:
                for ws in buff_props["WeaponSelectors"]:
                    tag = ws["ModuleTag"]
                    if tag is None:
                        continue
                    module_tag_id = ModuleTag.get_from_asset_path(tag["ObjectPath"], log_tabs=1)
                    weapon_selectors.append({"module_tag_id": module_tag_id})

                if weapon_selectors:
                    parsed_buff["weapon_selectors"] = weapon_selectors

            ability_selectors = []
            if 'AbilitySelectors' in buff_props:
                for aselector in buff_props["AbilitySelectors"]:
                    allowed_placement_types = []
                    for aptype in aselector["AllowedPlacementTypes"]:
                        allowed_placement_types.append(parse_colon_colon(aptype))
                    module_tags = []
                    for mtag in aselector["ModuleTags"]:
                        module_tag_id = ModuleTag.get_from_asset_path(mtag["ObjectPath"], log_tabs=1)
                        module_tags.append({"module_tag_id": module_tag_id})
                    
                    ability_selectors.append({
                        "allowed_placement_types": allowed_placement_types,
                        "module_tags": module_tags
                    })

                if ability_selectors:
                    parsed_buff["ability_selectors"] = ability_selectors

            if parsed_buff:
                parsed_buffs.append(parsed_buff)

        if parsed_buffs:
            return parsed_buffs
        return None
