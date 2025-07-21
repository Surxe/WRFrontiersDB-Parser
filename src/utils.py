from dotenv import load_dotenv
import os
import json
import re
load_dotenv()

###############################
#           Params            #
###############################
class Params:
    """
    A class to hold parameters for the application.
    """
    def __init__(self):
        self.export_path = os.getenv('EXPORTS_PATH')
        self.game_name = os.getenv('GAME_NAME')
        self.log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
        self.output_path = os.getenv('OUTPUT_PATH', None)
        self.validate()
        self.log()

    def validate(self):
        """
        Validates the parameters.
        """
        if not self.export_path:
            raise ValueError("EXPORTS_PATH environment variable is not set.")
        if not os.path.exists(self.export_path):
            raise ValueError(f"EXPORTS_PATH '{self.export_path}' does not exist.")

        if not self.game_name:
            raise ValueError("GAME_NAME environment variable is not set.")
        
        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"LOG_LEVEL {self.log_level} must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL.")

        # Create a default output path if not set
        if self.output_path is None:
            self.output_path = os.path.join(self.export_path, 'output')
            os.makedirs(self.output_path, exist_ok=True)
        if not os.path.exists(self.output_path):
            raise ValueError(f"OUTPUT_PATH '{self.output_path}' does not exist.")
        
    def log(self):
        """
        Logs the parameters.
        """
        print(f"Params initialized with:\n"
              f"EXPORTS_PATH: {self.export_path}\n"
              f"GAME_NAME: {self.game_name}\n"
              f"LOG_LEVEL: {self.log_level}\n"
              f"OUTPUT_PATH: {self.output_path}")

    def __str__(self):
        return f"Params(export_path={self.export_path}, game_name={self.game_name}, log_level={self.log_level})"

PARAMS = Params()  # Initialize global Params object

###############################
#             LOG             #
###############################

def log(message: str, tabs: int = 0) -> None:
    """
    Logs a message with a specified number of tabs for indentation.
    """
    if not isinstance(message, str):
        raise TypeError("Message must be a string.")
    if not isinstance(tabs, int) or tabs < 0:
        raise ValueError("Tabs must be a non-negative integer.")
    
    indent = '\t' * tabs
    if PARAMS.log_level == "DEBUG":
        print(f"{indent}{message}")


###############################
#             FILE            #
###############################

def get_json_data(file_path: str) -> dict:
    """
    Reads a JSON file and returns its content.
    """
    data = None
    with open(file_path, encoding='utf-8') as file:
        data = json.load(file)
    if data is None:
        raise ValueError(f"Error: {file_path} is empty or not a valid JSON file.")
    return data

def clear_dir(dir: str) -> None:
    for filename in os.listdir(dir):
        file_path = os.path.join(dir, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

###############################
#    Unreal Engine Parsing    #
###############################

# Converts "asset_path_name" or "ObjectPath" to the actual file path
def asset_path_to_file_path(asset_path):
    game_name = PARAMS.game_name
    # ObjectPath (DT) are suffixed with .<assetName> like path/to//assetName.assetName, return 0 index
        # "DungeonCrawler/Content/DungeonCrawler/ActorStatus/Buff/AbyssalFlame/GE_AbyssalFlame.0" -> "F:\DarkAndDarkerWiki\Exports\DungeonCrawler\Content\DungeonCrawler\ActorStatus\Buff\AbyssalFlame\GE_AbyssalFlame.json"
    # asset_path_name (V2) are prefixed with \Game instead of \DungeonCrawler\Content, and suffixed with .<index>
        # "/Game/DungeonCrawler/Maps/Dungeon/Modules/Crypt/Edge/Armory/Armory_A.Armory_A" -> "F:\DarkAndDarkerWiki\Exports\DungeonCrawler\Content\Maps\Dungeon\Modules\Crypt\Edge\Armory\Armory_A.json"
    return PARAMS.export_path + "\\" + asset_path.split('.')[0].replace("/Game/",f"\\{game_name}\\Content\\") + ".json"

# Converts "asset_path_name" or "ObjectPath" to the actual file path and the index of the asset
# when a asset/object path is referenced, the index corresponds to the specific element of the asset to jump to
# i.e. if file A references file B with index 2, it means within file B's json of [a, b, c], it will jump to the data within c
def asset_path_to_file_path_and_index(asset_path):
    index = asset_path.split('.')[-1]
    if index == "" or index is None: # ../Armor/Armor_A.5 -> 5
        raise Exception("No index found in asset_path: "+asset_path)
    if not index.isdigit(): #../Armory/Armory_A.Armory_A -> 0
        index = 0
    return asset_path_to_file_path(asset_path), int(index)


def asset_path_to_data(asset_path) -> dict: # "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> the data found within the file stored locally
    file_path, index = asset_path_to_file_path_and_index(asset_path)
    data = get_json_data(file_path)
    return data[index] #json via asset path is technically an array with just one element

def path_to_id(asset_path) -> str: # "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> "Id_LootDropGroup_GhostKing"
    # technically also works for file_path # "DungeonCrawler/ContentData/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> "Id_LootDropGroup_GhostKing"
    return asset_path.split("/")[-1].split(".")[0]

###############################
# Frequent Structure Parsing  #
###############################

# Parsers for common structures used in this specific game data
    
def parse_hex(data: dict):
    return data["Hex"]

def parse_colon_colon(data: str):
    return data.split("::")[-1] # i.e. "ESWeaponReloadType::X" -> "X"

###############################
#           String            #
###############################

def to_snake_case(text):
    """Convert text to snake_case"""
    # Insert underscore before uppercase letters that follow lowercase letters
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    # Insert underscore before uppercase letters that follow lowercase letters or numbers
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    # Replace spaces with underscores and convert to lowercase
    return s2.replace(' ', '_').lower()