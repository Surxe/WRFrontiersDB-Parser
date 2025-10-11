from dotenv import load_dotenv

import os
import json
import os
from loguru import logger
import shutil
import re
load_dotenv()
from options import init_options

OPTIONS = init_options()  # Initialize OPTIONS here to ensure it's available for functions below
# will be overridden by init_options from run.py if the args are used in addition to just env params

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

def clear_dir(dir_path: str) -> None:
    """Clear directory contents but keep the directory itself"""
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)

def normalize_path(path: str) -> str:
    """Normalize a file path to use forward slashes for cross-platform consistency."""
    # Use os.path.normpath to normalize the path properly for the current platform
    # This ensures drive letters and absolute paths are handled correctly
    normalized = os.path.normpath(path)
    # Only convert backslashes to forward slashes for display consistency in tests
    # but preserve the platform-specific absolute path characteristics
    return normalized.replace('\\', '/')

###############################
#    Unreal Engine Parsing    #
###############################

# Converts "asset_path_name" or "ObjectPath" to the actual file path
def asset_path_to_file_path(asset_path):
    # Ensure OPTIONS is initialized
    if OPTIONS is None:
        raise ValueError("OPTIONS not initialized. Call init_options() first.")
    
    game_name = OPTIONS.game_name
    # ObjectPath (DT) are suffixed with .<assetName> like path/to//assetName.assetName, return 0 index
        # "DungeonCrawler/Content/DungeonCrawler/ActorStatus/Buff/AbyssalFlame/GE_AbyssalFlame.0" -> "F:\DarkAndDarkerWiki\Exports\DungeonCrawler\Content\DungeonCrawler\ActorStatus\Buff\AbyssalFlame\GE_AbyssalFlame.json"
    # asset_path_name (V2) are prefixed with \Game instead of \DungeonCrawler\Content, and suffixed with .<index>
        # "/Game/DungeonCrawler/Maps/Dungeon/Modules/Crypt/Edge/Armory/Armory_A.Armory_A" -> "F:\DarkAndDarkerWiki\Exports\DungeonCrawler\Content\Maps\Dungeon\Modules\Crypt\Edge\Armory\Armory_A.json"
    
    # "BlueprintGeneratedClass'/Game/Sparrow/.../BP_Buff_A.BP_Buff_A_C'" -> use the part in quotes
    # if ' in asset path twice
    if "\'" in asset_path and asset_path.count("\'") == 2:
        asset_path = asset_path.split("\'")[1]
    
    # Convert the asset path to a relative path, replacing /Game/ with the appropriate game content path
    relative_path = asset_path.split('.')[0].replace("/Game/", f"{game_name}/Content/")
    # Convert forward slashes to the correct path separator for the current OS
    relative_path_parts = relative_path.split('/')
    
    # Normalize the export path first to ensure consistent separators
    normalized_export_dir = normalize_path(OPTIONS.export_dir)
    # Build the full file path using os.path.join for cross-platform compatibility
    file_path = os.path.join(normalized_export_dir, *relative_path_parts) + ".json"
    # Normalize the final path using our custom normalize_path function
    file_path = normalize_path(file_path)
    return file_path

def path_to_index(path: str) -> int:
    if '.' not in path:
        raise Exception("No index found in asset_path: "+path)
    index_str = path.split('.')[-1]
    if index_str == "" or index_str is None: # ../Armor/Armor_A.5 -> 5
        raise Exception("No index found in asset_path: "+path)
    if not index_str.isdigit(): #../Armory/Armory_A.Armory_A -> 0
        return 0
    return int(index_str)

# Converts "asset_path_name" or "ObjectPath" to the actual file path and the index of the asset
# when a asset/object path is referenced, the index corresponds to the specific element of the asset to jump to
# i.e. if file A references file B with index 2, it means within file B's json of [a, b, c], it will jump to the data within c
def asset_path_to_file_path_and_index(asset_path):
    index = path_to_index(asset_path)
    return asset_path_to_file_path(asset_path), index

def asset_path_to_data(asset_path) -> dict: # "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> the data found within the file stored locally
    file_path, index = asset_path_to_file_path_and_index(asset_path)
    data = get_json_data(file_path)
    return data[index] #json via asset path is technically an array with just one element

def path_to_file_name(asset_path) -> str:
    if asset_path in ['','.','/','//'] or asset_path is None:
        raise ValueError("Empty asset_path provided.")
    return asset_path.split('/')[-1].split('.')[0]

def path_to_id(asset_path) -> str: # "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> "Id_LootDropGroup_GhostKing"
    # technically also works for file_path # "DungeonCrawler/ContentData/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing" -> "Id_LootDropGroup_GhostKing.0"
    file_name = path_to_file_name(asset_path)
    index = path_to_index(asset_path)
    return f"{file_name}.{index}" # /path/to/DA_Thing.0 -> DA_Thing.0

###############################
# Frequent Structure Parsing  #
###############################

# Parsers for common structures used in this specific game data
    
def parse_hex(data: dict):
    data = data["SpecifiedColor"] if "SpecifiedColor" in data else data
    return data["Hex"]

def parse_colon_colon(data: str):
    split = data.split("::")
    if len(split) < 2:
        raise ValueError(f"Data '{data}' does not contain '::' to split.")
    if len(split) > 2:
        raise ValueError(f"Data '{data}' contains more than one '::'.")
    return split[-1] # i.e. "ESWeaponReloadType::X" -> "X"

expected_curve_data = {
    "TangentMode": "RCTM_Auto",
    "TangentWeightMode": "RCTWM_WeightedNone",
    "ArriveTangent": 0.0,
    "ArriveTangentWeight": 0.0,
    "LeaveTangent": 0.0,
    "LeaveTangentWeight": 0.0
}
def parse_editor_curve_data(data: dict):
    if 'DistToDamage' in data:
        dist_data = data["DistToDamage"]
    elif 'FloatCurve' in data:
        dist_data = data['FloatCurve']
    else:
        dist_data = data
    
    if 'EditorCurveData' in dist_data:
        dist_data = dist_data["EditorCurveData"]

    if 'KeyHandlesToIndices' in dist_data:
        del dist_data['KeyHandlesToIndices']
    if not dist_data:
        return

    if 'Keys' not in dist_data:
        return dist_data
    else:
        dist_data = dist_data["Keys"]

    parsed_curve = []
    for elem in dist_data:
        for expected_key, expected_value in expected_curve_data.items():
            if expected_key not in elem:
                raise ValueError(f"Missing expected key '{expected_key}' in curve data element")
            if elem[expected_key] != expected_value:
                raise ValueError(f"Unexpected value for key '{expected_key}' in curve data element: {elem[expected_key]} (expected: {expected_value})")
        interp_mode = elem["InterpMode"]
        parsed_elem = {
            "Time": elem["Time"],
            "Value": elem["Value"],
            "InterpMode": interp_mode
        }
        parsed_curve.append(parsed_elem)

    curve_data = parsed_curve

    if 'DistToDamage' in data:
        data["DistToDamage"] = curve_data
        return data
    return curve_data

###############################
#           String            #
###############################

def to_snake_case(text):
    """Convert text to snake_case"""
    # Remove pre-existing underscores to avoid double underscores
    s0 = text.replace('_', '')
    # Insert underscore before uppercase letters that follow lowercase letters
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s0)
    # Insert underscore before uppercase letters that follow lowercase letters or numbers
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    # Replace spaces with underscores and convert to lowercase
    s3 = s2.replace(' ', '_').lower()
    return s3.strip('_')


###############################
#        Dictionary           #
###############################

def sort_dict(d: dict, num_levels: int = -1) -> dict:
    """Recursively sort the first num_levels levels of a dictionary by keys."""
    # num_levels=-1 means sort all levels
    if not isinstance(d, dict):
        return d
    if num_levels == 0:
        return d
    num_levels = num_levels if num_levels > 0 else float('inf')
    sorted_dict = {}
    for key in sorted(d.keys()):
        sorted_dict[key] = sort_dict(d[key], num_levels - 1)
    return sorted_dict

EMPTY_VALUES = [None, "", [], {}]
def remove_blank_values(d: dict) -> dict:
    """Remove keys with blank values from a dictionary- recursively."""
    if d in EMPTY_VALUES:
        return d
    if not isinstance(d, dict):
        return d
    res = {}
    for k, v in d.items():
        if v not in EMPTY_VALUES:
            res_v = remove_blank_values(v)
            if res_v not in EMPTY_VALUES:
                res[k] = res_v
    return res

def merge_dicts(base: dict, overlay: dict) -> dict:
    """Recursively merge two dictionaries."""
    result = dict(base if base else {})
    if not overlay:
        return result
    for key, value in overlay.items():
        if value is not None and value != []:
            val1 = value
            val2 = result.get(key)
            type_1 = type(val1)
            type_2 = type(val2)
            if val1 is not None and val2 is not None and type_1 != type_2:
                raise TypeError(f"Type mismatch for key '{key}': {type_1} vs {type_2}")
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = merge_dicts(result[key], value)
            else:
                # use overlay's value
                result[key] = value
    return remove_blank_values(result)

class ParseAction:
    ATTRIBUTE = "attribute"
    DICT_ENTRY = "dict_entry"

class ParseTarget:
    MATCH_KEY = "match_key"           # Use the original key as-is
    MATCH_KEY_SNAKE = "match_key_snake"  # Convert key to snake_case

def process_key_to_parser_function(key_to_parser_function_map, data, obj=None, log_descriptor="", set_attrs=True, tabs=0, default_configuration={}):
    """
    Enhanced version that supports flexible target destinations.
    
    Configuration format:
    {
        "PropertyKey": {
            'parser': function_or_value,     # Optional: Parser function or "value" (default: "value")
            'action': ParseAction.ATTRIBUTE, # Optional: How to store the result (default: ParseAction.ATTRIBUTE)
            'target_dict_path': 'dict.nested', # Dict path with dot notation (only for DICT_ENTRY action)
            'target': ParseTarget.MATCH_KEY or "custom_name", # How to determine the key/attribute name
        }

        OR any of the following shortcuts:
        "PropertyKey": function or "value" # Will default to ParseAction.ATTRIBUTE and ParseTarget.MATCH_KEY_SNAKE

        "PropertyKey": (function, "key")  # Use function to parse and store as "key" - legacy format. Only needed over the above shortcut if key needs to be different to snake case.
    }
    
    Examples:
    "Regen amount": {
        'action': ParseAction.DICT_ENTRY,
        'target_dict_path': 'default_properties',
        'target': ParseTarget.MATCH_KEY,  # saves to obj.default_properties["Regen amount"]
    },
    "DamageBoost": {
        'action': ParseAction.DICT_ENTRY,
        'target_dict_path': 'default_properties',
        'target': "damage_boost",  # saves to obj.default_properties["damage_boost"]
    },
    "Stats": {
        'parser': some_parser_function,
        'target': "parsed_stats",  # saves to obj.parsed_stats
    }
    """
    
    if not isinstance(key_to_parser_function_map, dict):
        raise TypeError("key_to_parser_function must be a dictionary.")
    
    if set_attrs and obj is None:
        raise ValueError("obj must be provided when set_attrs=True")
    
    if log_descriptor != "":
        log_descriptor = f" in {log_descriptor}"

    # Get class name for logging
    class_name = obj.__class__.__name__ if obj else None

    # Determine the default configuration
    default_config_to_use = {
        'parser': "value",  # Default parser is "value"
        'action': ParseAction.ATTRIBUTE,  # Default action is to set an attribute
        'target_dict_path': None,  # Default is no nested dict path
        'target': ParseTarget.MATCH_KEY_SNAKE  # Default target is to match key in snake_case
    }
    # Update with any provided default configuration
    for key, value in default_configuration.items():
        if key in default_config_to_use:
            default_config_to_use[key] = value
        else:
            raise ValueError(f"Unknown default configuration key: {key}")
        
    parsed_data = dict()

    for key, value in data.items():
        # Remove trailing indexing from key if present
        # i.e. 'Id_ColorParam[2]' -> 'Id_ColorParam'
        if isinstance(key, str) and re.match(r'.+\[\d+\]$', key):
            key = re.sub(r'\[\d+\]$', '', key)

        if not key in key_to_parser_function_map:
            obj_id = getattr(obj, 'id', 'Error, no id found for obj') if obj else None
            obj_class_ref_str = f"{class_name} {obj_id} has unknown property" if class_name and obj_id else "Unknown property"
            logger.warning(f"Warning: {obj_class_ref_str} '{key}'{log_descriptor}", tabs=tabs)
        
        else:
            config = key_to_parser_function_map[key]
            
            # Handle None (skip processing)
            if config is None:
                continue
            
            # Handle function directly - use as parser with defaults
            if callable(config) or config == "value":
                config = {
                    'parser': config,
                }
            
            # Handle legacy tuple format for backwards compatibility
            elif isinstance(config, tuple):
                config = {
                    'parser': config[0],
                    'target': config[1]
                }
            
            # Handle new dictionary format
            if not isinstance(config, dict):
                raise TypeError(f"{class_name} Value for key '{key}' must be a dict, tuple, callable, or None, got {type(config)}")

            parser = config.get('parser', default_config_to_use['parser'])
            action = config.get('action', default_config_to_use['action'])
            target_dict_path = config.get('target_dict_path', default_config_to_use['target_dict_path'])
            target = config.get('target', default_config_to_use['target'])
            
            # Validate configuration
            if action == ParseAction.DICT_ENTRY and not target_dict_path:
                raise ValueError(f"{class_name} target_dict_path required for DICT_ENTRY action on key '{key}'")
            elif action == ParseAction.ATTRIBUTE and target_dict_path:
                #raise ValueError(f"{class_name} target_dict_path should not be provided for ATTRIBUTE action on key '{key}'")
                # this is now allowed for defaulting it in configuration. Its simply ignored if not DICT_ENTRY
                pass
            
            # Parse the value
            if parser == "value":
                parsed_value = value
            elif callable(parser):
                parsed_value = parser(value)
            else:
                raise TypeError(f"{class_name} Parser for key '{key}' must be callable or 'value', got {type(parser)}")
            
            if parsed_value is None:
                continue
            
            # Determine target name
            if target == ParseTarget.MATCH_KEY:
                target_name = key
            elif target == ParseTarget.MATCH_KEY_SNAKE:
                target_name = to_snake_case(key)
            elif isinstance(target, str):
                # Custom string target
                target_name = target
            else:
                raise ValueError(f"{class_name} Target must be ParseTarget.MATCH_KEY, ParseTarget.MATCH_KEY_SNAKE, or a string for key '{key}', got {type(target)}")
            
            # Store the parsed value
            if action == ParseAction.ATTRIBUTE:
                # Direct attribute assignment
                if set_attrs:
                    setattr(obj, target_name, parsed_value)
                else:
                    parsed_data[target_name] = parsed_value
                    
            elif action == ParseAction.DICT_ENTRY:
                # Handle dot notation for nested dictionaries
                path_parts = target_dict_path.split('.')
                
                if set_attrs:
                    current = obj
                    # Navigate/create the nested structure
                    for part in path_parts:
                        if isinstance(current, dict):
                            # Current is a dictionary, use dictionary access
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        else:
                            # Current is an object, use attribute access
                            if not hasattr(current, part):
                                setattr(current, part, {})
                            current = getattr(current, part)
                    current[target_name] = parsed_value
                else:
                    # For non-attribute setting, store in nested structure
                    current = parsed_data
                    for part in path_parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    if path_parts[-1] not in current:
                        current[path_parts[-1]] = {}
                    current[path_parts[-1]][target_name] = parsed_value

    if not set_attrs:
        return parsed_data