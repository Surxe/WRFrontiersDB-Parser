# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

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

    def _p_bp(self, data: dict): #TODO
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
            "Regen amount": (self._p_regen_amount, None),
            "Effect": None,
            "DamageBoost": (self._p_damage_boost, None),
            "ArmorToRestore": (self._p_armor_to_restore, None),
            "AdditionalFuel": (self._p_additional_fuel, None),
            "TorsoFx": None,
            "VisualEffect": None,
            "SoundEffect": None,
            "Stream": None,
            "MaxStacks": (self._p_max_stacks, None),
            "TitanPoints": (self._p_titan_points, None),
            "ChargeToAdd": (self._p_charge_to_add, None),
            "Stats": (self._p_stats, "stats"),
            "Trigger": None,
            "Buffs": (self._p_buffs, "buffs"),
            "ActivationReaction": None,
            "Lifetime": (self._p_lifetime, None),
            "OnActivateAkEvent": None,
            "OnDeactivateAkEvent": None,
            "bIsInfinity": None,
        }

        self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor=bp_file_path, tabs=2)

    def _p_default_property(self, property_key, property_value):
        if not hasattr(self, "default_properties"):
            self.default_properties = dict()

        self.default_properties[property_key] = property_value

    def _p_regen_amount(self, data: dict):
        self._p_default_property("Regen amount", data)

    def _p_damage_boost(self, data: dict):
        self._p_default_property("DamageBoost", data)

    def _p_armor_to_restore(self, data: dict):
        self._p_default_property("ArmorToRestore", data)

    def _p_additional_fuel(self, data: dict):
        self._p_default_property("AdditionalFuel", data)

    def _p_max_stacks(self, data: dict):
        self._p_default_property("MaxStacks", data)

    def _p_titan_points(self, data: dict):
        self._p_default_property("TitanPoints", data)

    def _p_charge_to_add(self, data: dict):
        self._p_default_property("ChargeToAdd", data)

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

    def _p_lifetime(self, data: dict):
        self._p_default_property("Lifetime", data)
        