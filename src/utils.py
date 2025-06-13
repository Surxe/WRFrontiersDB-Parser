from dotenv import load_dotenv
import os
import json
load_dotenv()

###############################
#             JSON            #
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



###############################
#    Unreal Engine Parsing    #
###############################

# Converts "asset_path_name" or "ObjectPath" to the actual file path
def asset_path_to_file_path(asset_path):
    game_name = os.getenv('GAME_NAME', 'DungeonCrawler') 
    # ObjectPath (DT) are suffixed with .<assetName> like path/to//assetName.assetName, return 0 index
        # "DungeonCrawler/Content/DungeonCrawler/ActorStatus/Buff/AbyssalFlame/GE_AbyssalFlame.0" -> "F:\DarkAndDarkerWiki\Exports\DungeonCrawler\Content\DungeonCrawler\ActorStatus\Buff\AbyssalFlame\GE_AbyssalFlame.json"
    # asset_path_name (V2) are prefixed with \Game instead of \DungeonCrawler\Content, and suffixed with .<index>
        # "/Game/DungeonCrawler/Maps/Dungeon/Modules/Crypt/Edge/Armory/Armory_A.Armory_A" -> "F:\DarkAndDarkerWiki\Exports\DungeonCrawler\Content\Maps\Dungeon\Modules\Crypt\Edge\Armory\Armory_A.json"
    return os.getenv('EXPORTS_PATH') + "\\" + asset_path.split('.')[0].replace("/Game/",f"\\{game_name}\\Content\\") + ".json"

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
    file_path = asset_path_to_file_path(asset_path)
    data = get_json_data(file_path)
    return data[0] #json via asset path is technically an array with just one element

def asset_path_to_id(asset_path) -> str: # "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> "Id_LootDropGroup_GhostKing"
    return asset_path.split("/")[-1].split(".")[0]