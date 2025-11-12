# Add parent dirs to sys path
import sys
import os

from loguru import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parse.parsers.ability import p_actor_class
from parsers.object import ParseObject
from parsers.localization_table import parse_localization
from parsers.image import parse_image_asset_path
from parsers.module_stat import ModuleStat

from utils import ParseTarget, ParseAction, asset_path_to_data, asset_path_to_file_path, get_json_data, parse_colon_colon

class PilotTalent(ParseObject):
    objects = dict()  # Dictionary to hold all PilotTalent instances

    def _parse(self):
        props = self.source_data["Properties"]

        key_to_parser_function = {
            "Name": parse_localization,  # Changed: "Name" → "name"
            "Description": parse_localization,  # Changed: "Description" → "description"
            "UIDescription": (parse_localization, "ui_description"),  # Keep: "UIDescription" → "u_i_description" != "ui_description"
            "ShortUIDescription": (parse_localization, "short_ui_description"),  # Keep: complex conversion
            "Image": (parse_image_asset_path, "image_path"),  # Keep: "Image" → "image" != "image_path"
            "PilotTalent": (self._p_bp, None),
            "ID": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor='PilotTalent')

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
            "VfxClass": None,
            "Cooldown": "value",
            "BuffClass": p_actor_class,
            
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

            "EffectLoopStart": None, #voicelines for field repairs
            "EffectLoopStop": None,
            
            # Regular attributes
            "Stats": self._p_stats,
            "Buffs": self._p_buffs,
            "TargetBuffs": self._p_buffs,

            "ReactivationPolicy": parse_colon_colon,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor=bp_file_path)

    def _p_stats(self, stats):
        parsed_stats = []
        for stat in stats:
            stat_id = ModuleStat.get_from_asset_path(stat["Key"].split('SModuleStatInfo\'')[1])
            value = stat["Value"]
            parsed_stats.append({
                "stat_id": stat_id,
                "value": value
            })

        if parsed_stats:
            return parsed_stats
        return

    def _p_buffs(self, buffs: list):
        logger.debug(f"Parsing {len(buffs)} buffs for {self.id}")
        parsed_buffs = []
        
        for buff in buffs:
            parsed_buff = {}

            buff_asset_path = buff["ObjectPath"]
            buff_data = asset_path_to_data(buff_asset_path)

            parsed_buff = p_actor_class(buff_data["ClassDefaultObject"])

            if parsed_buff:
                parsed_buffs.append(parsed_buff)

        if parsed_buffs:
            return parsed_buffs
        return
