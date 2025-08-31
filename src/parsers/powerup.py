# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import log, get_json_data, asset_path_to_data, PARAMS, merge_dicts, parse_hex
from parsers.ability import p_actor_class
from parsers.image import parse_image_asset_path

from parsers.object import Object
from parsers.image import Image

class Powerup(Object):
    objects = dict()

    def _parse(self):
        # Wrapper for main ability parsing
        return self._parse_from_data(self.source_data)
    
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
            "ID": None,
        }

        my_powerup_data = self._process_key_to_parser_function(key_to_parser_function, props, tabs=2)

        overlayed_data = merge_dicts(template_ability_data, my_powerup_data)

        for key, value in overlayed_data.items():
            setattr(self, key, value)

    def _p_actor_class(self, data: dict):
        return p_actor_class(self, data)

def parse_powerup_wrapper(full_path, id):
    log(f"Parsing {Powerup.__name__} {id} from {full_path}", tabs=0)
    powerup_data = asset_path_to_data(get_json_data(full_path)[0]["ClassDefaultObject"]["ObjectPath"])
    powerup = Powerup(id, powerup_data)
    return powerup

def parse_powerups(to_file=False):
    powerups_source_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Sparrow\Mechanics\Powerups")
    
    subdirs = ['Personal', 'Teams']
    for subdir in subdirs:
        powerups_subdir_path = os.path.join(powerups_source_path, subdir)

        # Teams/DamageResist, Teams/RegenArmor, Teams/UltimateCharge, etc.
        # Personal/DoubleDamage, Personal/RechargeAbilities, etc.
        for dir in os.listdir(powerups_subdir_path):
            # Skip if its a file and not a dir, like Powerups/Teams/BP_PowerUp_TeamBuffs (a template file)
            if not os.path.isdir(os.path.join(powerups_subdir_path, dir)):
                continue
            
            for file in os.listdir(os.path.join(powerups_subdir_path, dir)):
                if 'Indicator' in file:
                    continue #not actual powerups
                id = file.split('.')[0]
                file_path = os.path.join(powerups_subdir_path, dir, file)
                parse_powerup_wrapper(file_path, id)

    if to_file: # Condition prevents needlessly saving the same data multiple times, as it will also be saved if ran thru parse.py
        Powerup.to_file()
        Image.to_file()

if __name__ == "__main__":
    parse_powerups(to_file=True)