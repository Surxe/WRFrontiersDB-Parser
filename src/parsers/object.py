# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import PARAMS, path_to_id, asset_path_to_file_path_and_index, get_json_data, log, to_snake_case

import json

class Object: #generic object that all classes extend
    objects = dict()  # Dictionary to hold all object instances

    def __init__(self, id: str = "", source_data: dict = {}):
        self.source_data = source_data
        self.id = id
        if id == "" and source_data == {}:
            return
        self._parse()

        self.objects[id] = self  # Store the instance in the class dictionary

    def _parse(self):
        """
        This method should be overridden by subclasses to parse the source data.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def _process_key_to_parser_function(self, key_to_parser_function_map, data, log_descriptor="", set_attrs=True, tabs=0, default_configuration={}):
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
            'target': ParseTarget.MATCH_KEY,  # saves to self.default_properties["Regen amount"]
        },
        "DamageBoost": {
            'action': ParseAction.DICT_ENTRY,
            'target_dict_path': 'default_properties',
            'target': "damage_boost",  # saves to self.default_properties["damage_boost"]
        },
        "Stats": {
            'parser': self._p_stats,
            'target': "parsed_stats",  # saves to self.parsed_stats
        }
        """
        
        if not isinstance(key_to_parser_function_map, dict):
            raise TypeError("key_to_parser_function must be a dictionary.")
        
        if log_descriptor != "":
            log_descriptor = f" in {log_descriptor}"

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
            if key in key_to_parser_function_map:
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
                    raise TypeError(f"{self.__class__.__name__} Value for key '{key}' must be a dict, tuple, callable, or None, got {type(config)}")

                parser = config.get('parser', default_config_to_use['parser'])
                action = config.get('action', default_config_to_use['action'])
                target_dict_path = config.get('target_dict_path', default_config_to_use['target_dict_path'])
                target = config.get('target', default_config_to_use['target'])
                
                # Validate configuration
                if action == ParseAction.DICT_ENTRY and not target_dict_path:
                    raise ValueError(f"{self.__class__.__name__} target_dict_path required for DICT_ENTRY action on key '{key}'")
                elif action == ParseAction.ATTRIBUTE and target_dict_path:
                    #raise ValueError(f"{self.__class__.__name__} target_dict_path should not be provided for ATTRIBUTE action on key '{key}'")
                    # this is now allowed for defaulting it in configuration. Its simply ignored if not DICT_ENTRY
                    pass
                
                # Parse the value
                if parser == "value":
                    parsed_value = value
                elif callable(parser):
                    parsed_value = parser(value)
                else:
                    raise TypeError(f"{self.__class__.__name__} Parser for key '{key}' must be callable or 'value', got {type(parser)}")
                
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
                    raise ValueError(f"{self.__class__.__name__} Target must be ParseTarget.MATCH_KEY, ParseTarget.MATCH_KEY_SNAKE, or a string for key '{key}', got {type(target)}")
                
                # Store the parsed value
                if action == ParseAction.ATTRIBUTE:
                    # Direct attribute assignment
                    if set_attrs:
                        setattr(self, target_name, parsed_value)
                    else:
                        parsed_data[target_name] = parsed_value
                        
                elif action == ParseAction.DICT_ENTRY:
                    # Handle dot notation for nested dictionaries
                    path_parts = target_dict_path.split('.')
                    
                    if set_attrs:
                        current = self
                        # Navigate/create the nested structure
                        for part in path_parts:
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
            
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'{log_descriptor}", tabs=tabs)

        if not set_attrs:
            return parsed_data

    def to_dict(self):
        """
        Returns a dictionary representation of the object, excluding source_data.
        """
        obj_as_dict = self.__dict__
   
        keys_to_remove = ['source_data']
        for key in keys_to_remove:
            if key in obj_as_dict:
                del obj_as_dict[key]
        return obj_as_dict

    @classmethod
    def get_from_id(cls, id, create_if_missing=False):
        """
        Returns an object from the class dictionary by its ID.
        If the object does not exist and create_if_missing is True, it creates a new instance.
        """
        if id not in cls.objects:
            if create_if_missing:
                return cls(id)
            else:
                return None
        else:
            return cls.objects[id]
        
    @classmethod
    def get_from_asset_path(cls, asset_path: str, log_tabs: int = 1, sub_index=True, create_if_missing=True) -> str:
        """
        Returns the ID of an object from its asset path.
        If the object does not exist, it creates a new instance by parsing the asset file.
        sub_index: Whether to use the sub-index when parsing the asset file.
        """
        obj_id = path_to_id(asset_path)
        obj = cls.get_from_id(obj_id)
        if obj is None and create_if_missing:
            file_path, index = asset_path_to_file_path_and_index(asset_path)
            log(f"Parsing {cls.__name__} {obj_id} from {file_path} . {index}", tabs=log_tabs)
            obj_data = get_json_data(file_path)
            if sub_index:
                obj_data = obj_data[index]
            obj = cls(obj_id, obj_data)

        return obj_id

    @classmethod
    def objects_to_dict(cls):
        """
        Returns a dictionary representation of all objects
        """

        new_dict = {obj_id: obj.to_dict() for obj_id, obj in cls.objects.items()}

        return new_dict
    
    @classmethod
    def to_json(cls):
        """
        Returns a JSON string representation of all objects.
        """
        return json.dumps(cls.objects_to_dict(), indent=4, ensure_ascii=False)
    
    @classmethod
    def to_file(cls):
        file_path = os.path.join(PARAMS.output_path, f'{cls.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cls.to_json())

class ParseAction:
    ATTRIBUTE = "attribute"
    DICT_ENTRY = "dict_entry"

class ParseTarget:
    MATCH_KEY = "match_key"           # Use the original key as-is
    MATCH_KEY_SNAKE = "match_key_snake"  # Convert key to snake_case