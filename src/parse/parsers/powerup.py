# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, get_json_data, asset_path_to_data, OPTIONS, merge_dicts, parse_hex, path_to_id
from parsers.ability import p_actor_class
from parsers.image import parse_image_asset_path

from parsers.object import ParseObject
from parsers.image import Image

class Powerup(ParseObject):
    objects = dict()

    def _parse(self):
        # Wrapper for main ability parsing
        overlayed_data = self._parse_from_data(self.source_data)
        for key, value in overlayed_data.items():
            setattr(self, key, value)
    
    def _parse_from_data(self, source_data: dict):
        props = source_data["Properties"]

        template_ability_data = None
        if 'Template' in source_data:
            template_ability_data = self._parse_and_merge_template(source_data["Template"])

        key_to_parser_function = {
            "AttachedBuff": self._p_actor_class,
            "BuffDuration": "value",
            "MinimapIcon": (parse_image_asset_path, "icon_path"),
            "MinimapIconTint": (parse_hex, "icon_hex"),
            "Root": None,
            "OverlapComponent": None,
            "MeshComponent": None,
            "ReactionTypeTouchedActor": None,
            "CapturedByFriendlyTeamMessage": None,
            "RootComponent": None,
            "UberGraphFrame": None,
            "Level": None, #"HighGround" for all, unknown usage
            "SpawnSound": None,
            "ConsumeSound": None,
            "ReactionTypeTouchedActor": None,
            "RotationSpeed": None,
            "SpawnAnnouncer": None,
            "CapturedByEnemyTeamMessage": None,
            "Score": "value",
            "VFXClass": None,
            "CorpseDuration": None,
            "VFXLocation": None,
            "ID": None,
        }

        my_powerup_data = self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

        overlayed_data = merge_dicts(template_ability_data, my_powerup_data)

        return overlayed_data

    def _p_actor_class(self, data: dict):
        return p_actor_class(data)

def parse_powerup_wrapper(full_path, id):
    if 'Indicator' in full_path:
        return
    logger.debug(f"Parsing {Powerup.__name__} {id} from {full_path}")
    powerup_data = asset_path_to_data(get_json_data(full_path)[0]["ClassDefaultObject"]["ObjectPath"])
    powerup = Powerup(id, powerup_data)
    return powerup

def parse_powerups(to_file=False):
    powerups_source_path = os.path.join(OPTIONS.export_dir, r"WRFrontiers\Content\Sparrow\Mechanics\Powerups")
    
    # Maybe in the future the map files can be parsed directly which contains paths to the powerups. For now this will do.
    subdirs = ['Personal', 'Teams']
    # Check if Personal & Teams folders exist first
    use_subdirs = all(os.path.exists(os.path.join(powerups_source_path, subdir)) for subdir in subdirs) #they don't exist
    #pre 8-26-2025 there were only personal powerups which were stored here directly, not in subdirs
        
    if use_subdirs:
        for subdir in subdirs:
            powerups_subdir_path = os.path.join(powerups_source_path, subdir)

            # Teams/DamageResist, Teams/RegenArmor, Teams/UltimateCharge, etc.
            # Personal/DoubleDamage, Personal/RechargeAbilities, etc.
            for dir in os.listdir(powerups_subdir_path):
                # Skip if its a file and not a dir, like Powerups/Teams/BP_PowerUp_TeamBuffs (a template file)
                if not os.path.isdir(os.path.join(powerups_subdir_path, dir)):
                    continue
                
                for file in os.listdir(os.path.join(powerups_subdir_path, dir)):
                    file_path = os.path.join(powerups_subdir_path, dir, file)
                    id = file.split('.')[0]
                    parse_powerup_wrapper(file_path, id)

    else:
        for file in os.listdir(powerups_source_path):
            if not file.startswith("BP_PowerUp_"):
                continue
            file_path = os.path.join(powerups_source_path, file)
            id = file.split('.')[0]
            parse_powerup_wrapper(file_path, id)

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        Powerup.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_powerups(to_file=True)