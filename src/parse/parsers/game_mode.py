# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ParseTarget, parse_colon_colon, logger, get_json_data, asset_path_to_file_path_and_index, asset_path_to_data, path_to_id, asset_path_to_file_path, OPTIONS, parse_editor_curve_data
from parsers.localization_table import parse_localization

from parsers.object import ParseObject
from parsers.ability import p_actor_class
from parsers.bot_names import BotNames
from parsers.honor_reward import HonorReward

class GameMode(ParseObject):
    objects = dict()

    def _parse(self):
        props = self.source_data[0]["Properties"]
        
        key_to_parser_function = {
            "DisplayName": parse_localization,
            "Description": parse_localization,
            "Icon": None, #the icon may be an Engine asset, which is not downloaded
            "Name": None, #non-localized name
            "ID": None
        }

        self._process_key_to_parser_function(key_to_parser_function, props)

    def _parse_bp(self, bp_path: str):
        bp_data = get_json_data(bp_path)
        cdo_path = bp_data[0]["ClassDefaultObject"]["ObjectPath"]
        cdo_file_path, index = asset_path_to_file_path_and_index(cdo_path)
        logger.debug(f"Parsing {self.__class__.__name__} BP data from {cdo_file_path}")
        cdo_data = get_json_data(cdo_file_path)[index]
        props = cdo_data["Properties"]

        key_to_parser_function = {
            "WarpProveIsAlmostExpired": None, #announcer voice lines
            "WarpProbeIsAlmostExhausted": None,
            "WarpProbeActivated": None,
            "OurTeamCloseToVictoryMessageClass": None,
            "EnemyTeamCloseToVictoryMessageClass": None,
            "KillingSpreeLocalMessage": None,
            "HUDClass": None, #UI
            "BackandGameModeDA": None, #references what seems to be a dummy gamemode, "QuickMatch"
            "SubLevels": None, #contains some flags like Suffix, bMandatory, bVisible, bBlocking
            "SpawnerComponentsController": None,
            "WinScore": "value",
            "MatchRewardConfig": (self._p_match_reward, "match_rewards"),
            "MatchTimeLimitMinutes": "value",
            "KillCamLifetime": "value",
            "DropTimeLimitSeconds": "value",
            "AISquadClass": None, # spearhead AI is different to other AI it seems
            "BaseProtectionBuff": (self._p_actor_class, "base_protection_buff"),
            "RegenPercent": "value",
            "RegenDelay": "value",
            "RegenTickDuration": "value",
            "TitanSettings": (self._p_titan_settings, "titan_settings"),
            "AbilityChargeSettings": (self._p_ability_charge_settings, "ability_charge_settings"),
            "KillCameraActorClass": None,
            "BotNames": (self._p_bot_names, "bot_names"),
            "RibbonSystemClass": None,
            "PostCombatPipelineClass": None, #UI
            "HonorSystemClass": (self._p_honor_system, "honor_system"),
            "DefaultPawnClass": None,
            "DefaultBotsConfig": None, #Intermediate for all modes; overridden server side by the list in meta root
            "DefaultPlayerName": None, #"Terminator" lmao
            "TitanSpawnScoreThreshold": "value", #0 for tdm?
            "RobotBlockTimeReductionOnMechKillSeconds": "value",
            "RobotBlockTimeReductionOnTitanKillSeconds": "value",
            "RobotBlockTimeReductionOnArmorDestructionSeconds": "value",
            "ScorePerTitanKill": "value",
            "InitialRobotBlockTimeSeconds": "value",
            "EnemyTeamControlsMoreBeaconsMessageClass": None, #announce
            "OurTeamCloseToVictoryMessageClass": None, 
            "OurTeamControlsMoreBeaconsMessageClass": None,
            "EnemyTeamCloseToVictoryMessageClass": None,
            "PointsPerBeaconsDiff": self._p_beacon_pts,
            "TeamControlsMoreBeaconsThreshold": "value",
            "WarpProbeSelectionMethod": parse_colon_colon,
            "FirstWarpProbeSettings": self._p_warp_probe_settings,
            "InactivePlayerStateLifeSpan": "value", #spearhead
        }

        parsed_data = self._process_key_to_parser_function(key_to_parser_function, props, log_descriptor="BP", set_attrs=False, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })
        
        # Store data that wasn't parsed separately into defaultable_data
        other_data = dict()
        keys_to_store_as_attrs = ['match_rewards', 'base_protection_buff', 'titan_settings', 'ability_charge_settings', 'honor_system', 'bot_names']
        for key, value in parsed_data.items():
            if key not in keys_to_store_as_attrs:
                other_data[key] = value
            else:
                setattr(self, key, value)

        # Only store in obj if not empty
        if other_data:
            self.misc = other_data

    def _p_warp_probe_settings(self, data):
        return parse_colon_colon(data["SelectionMethod"])

    def _p_match_reward(self, data):
        data = asset_path_to_data(data["ObjectPath"])
        parsed_data = dict()
        for key, value in data["Properties"].items():
            if key != "ID":
                parsed_data[key] = value
        return parsed_data
        
    def _p_actor_class(self, data):
        return p_actor_class(data)

    def _p_titan_settings(self, data):
        data = asset_path_to_data(data["ObjectPath"])["Properties"]
        
        key_to_parser_function = {
            "TitanCharge": "value",
            "MechKill": "value",
            "TitanKill": "value",
            "BeaconSteal": "value",
            "BeaconCapture": "value",
            "LastMechLost": "value",
            "TitansDiff": parse_editor_curve_data,
            "ScoreDiff": parse_editor_curve_data,
            "TitanReadyMessageClass": None,
            "EnemyTeamDeployedTitanMessageClass": None,
            "BeaconHold": "value",
            "bCanSpawnTitanWhileAlive": "value",
        }

        return self._process_key_to_parser_function(key_to_parser_function, data, set_attrs=False, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })

    def _p_ability_charge_settings(self, data):
        data = asset_path_to_data(data["ObjectPath"])
        if 'Properties' not in data:
            return
        data = data["Properties"]

        key_to_parser_function = {
            "PointsForBeaconNeutralization": "value",
            "PointsForBeaconCapture": "value",
            "PointsForBeaconHold": "value",
        }

        return self._process_key_to_parser_function(key_to_parser_function, data, set_attrs=False, default_configuration={
            'target': ParseTarget.MATCH_KEY
        })

    def _p_bot_names(self, data):
        return BotNames.get_from_asset_path(data["ObjectPath"])
        
    def _p_honor_system(self, data):
        data = asset_path_to_data(data["ObjectPath"])
        data = asset_path_to_data(data["ClassDefaultObject"]["ObjectPath"])
        if 'Properties' not in data:
            return
        data = data["Properties"]["Rewards"]
        ids = []
        for honor_reward in data:
            honor_reward_id = HonorReward.get_from_asset_path(honor_reward["ObjectPath"])
            ids.append(honor_reward_id)
        return ids

    def _p_beacon_pts(self, data):
        parsed_data = dict()
        for elem in data:
            key = elem["Key"]
            value = elem["Value"]
            parsed_data[key] = value
        return parsed_data

def parse_game_modes(to_file=False):
    root_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\DA_Meta_Root.json")
    root_data = get_json_data(root_path)
    game_modes = root_data[0]["Properties"]["GameModes"]
    for game_mode_entry in game_modes:
        game_mode_asset_path = game_mode_entry["ObjectPath"]
        game_mode_id = path_to_id(game_mode_asset_path)
        game_mode_file_path = asset_path_to_file_path(game_mode_asset_path)
        game_mode_data = get_json_data(game_mode_file_path)

        # Manually map to the game mode setting file, which is separate to the name & description container file, and only connected server side
        game_mode_id_to_bp_path = {
            "DA_GameMode_BeaconRush.0": r"GameModes\Beacon\BP_GameMode_Beacon.json",
            "DA_GameMode_Elimination.0": r"GameModes\Elimination\BP_GameMode_Elimination.json",
            "DA_GameMode_TeamDeathMatch.0": r"GameModes\TeamDeathMatch\BP_GameMode_TeamDeathMatch.json",
            "DA_GameMode_Spearhead.0": r"GameModes\Spearhead\BP_GameMode_Spearhead.json"
        }

        # Only parse gamemodes that have a localized display name, these are actual game modes. Others include Hangar, tutorial, title menu, or even just list of bot names
        if 'Properties' in game_mode_data[0]:
            if 'DisplayName' in game_mode_data[0]['Properties']:
                if 'CultureInvariantString' not in game_mode_data[0]['Properties']["DisplayName"]:
                    logger.debug(f"Parsing {GameMode.__name__} {game_mode_id} from {game_mode_file_path}")
                    game_mode = GameMode(game_mode_id, game_mode_data)
                    game_mode._parse_bp(os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow", game_mode_id_to_bp_path[game_mode_id]))

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        GameMode.to_file()
        BotNames.to_file()
        HonorReward.to_file()

if __name__ == "__main__":
    parse_game_modes(to_file=True)