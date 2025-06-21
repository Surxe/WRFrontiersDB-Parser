from dotenv import load_dotenv
import os
import json
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
            raise ValueError("LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL.")
        
        # Create a default output path if not set
        if self.output_path is None:
            self.output_path = os.path.join(self.export_path, 'output')
            os.makedirs(self.output_path, exist_ok=True)
        if not os.path.exists(self.output_path):
            raise ValueError(f"OUTPUT_PATH '{self.output_path}' does not exist.")

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

def clear_dir(dir):
    dir = "data"
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
def parse_badge_visual_info(data: dict):
    """
    Parses the BadgeVisualInfo structure from the given data.
    Returns (image_id, tint_hex)
    """
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary.")
    
    image_id = None
    if "Image" in data and "AssetPathName" in data["Image"]:
        image_id = path_to_id(data["Image"]["AssetPathName"])
    
    tint_hex = None
    if 'TintColor' in data and 'Hex' in data["TintColor"]:  
        tint_hex = data["TintColor"]["Hex"]
    
    return image_id, tint_hex

def parse_localization(data: dict):
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary.")
    
    localization_key = None
    if "Key" in data:
        localization_key = data["Key"]
    
    localization_table_id = None
    if "TableId" in data:
        localization_table_id = path_to_id(data["TableId"])

    invariant_string = None
    if "CultureInvariantString" in data:
        invariant_string = data["CultureInvariantString"]  
    
    if localization_key is not None and localization_table_id is not None:
        return {
            "Key": localization_key,
            "TableId": localization_table_id
        }
    elif invariant_string is not None:
        return {
            "InvariantString": invariant_string
        }
    else:
        return None