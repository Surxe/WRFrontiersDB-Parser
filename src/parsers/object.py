
# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import PARAMS, path_to_id, asset_path_to_file_path, get_json_data, log

import json

class Object: #generic object that all classes extend
    objects = dict()  # Dictionary to hold all object instances
    
    def __init__(self, id: str, source_data: dict):
        self.source_data = source_data
        self.id = id
        self._parse()

        self.objects[id] = self  # Store the instance in the class dictionary

    def _parse(self):
        """
        This method should be overridden by subclasses to parse the source data.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def _process_key_to_parser_function(self, key_to_parser_function_map, data, log_descriptor="", set_attrs=True, tabs=0):
        """
        Processes a key-to-parser function mapping and applies the functions to the data.
        Sets the specified instance's attributes to the value returned by the function, or to datap[key] directly if the function is "value".
        If a key within data is not found in the map, it will log a warning to specify how/if it should be parsed.
 
        Requiring keys that could be present to be specified as None means if the data structure changes in the future, a warning can be raised very directly.

        key_to_parser_function_map = {
            "HumanName": (self._p_human_name, "name"), # call self._p_human_name(data) and store the result in parsed_data["name"]
            "TutorialTargetTag": None, # no function to call, skip this key
            "Description": ("value", "description"), # set data["Description"] directly in parsed_data["description"]. Figured using this with tuple instead of just "description" and checking type would be advantageous in the future
            "SomeOtherKey": ("value", "key"), # store data["SomeOtherKey"] directly in parsed_data["SomeOtherKey"]
            "SomeOtherOtherKey": (self._p_some_other_other_key, None) # call self._p_some_other_other_key(data) but the function does not return anything so no data to be stored at this stage
        }
        data = {
            "HumanName": {data to parse},
            "TutorialTargetTag": "SomeTag",
            "UniqueStuffID": "SomeData" # This key is not in the map, so it will print a warning to handle the key and either add a parser function or mark it with None
        }

        set_attrs: bool. If True, the instance's attributes will be set to the parsed data instead of returning parsed_data

        log_descriptor: str. A string to add at the end of the log message when a key is not found, used to add context.
        """

        if not isinstance(key_to_parser_function_map, dict):
            raise TypeError("key_to_parser_function must be a dictionary.")
        
        if log_descriptor != "":
            log_descriptor = f" in {log_descriptor}"
        
        parsed_data = dict()

        for key, value in data.items():
            if key in key_to_parser_function_map:
                function_attr = key_to_parser_function_map[key]
                if function_attr is None:
                    continue
                elif isinstance(function_attr, tuple):
                    function, attr = function_attr
                    if attr == "key":
                        key_to_store_value_in = attr
                    else:
                        key_to_store_value_in = attr if attr is not None else key

                    if function == "value":
                        value_to_set_attr_to = value
                    elif callable(function):
                        value_to_set_attr_to = function(value)
                    else:
                        raise TypeError(f"{self.__class__.__name__} Value for key '{key}' in key_to_parser_function_map must be a callable or 'value', got {type(function)}")
                else:
                    raise TypeError(f"{self.__class__.__name__} Value for key '{key}' in key_to_parser_function_map must be a tuple or None, got {type(function_attr)}")

                if value_to_set_attr_to is not None: # supports function not actually returning any value
                    parsed_data[key_to_store_value_in] = value_to_set_attr_to
            else:
                log(f"Warning: {self.__class__.__name__} {self.id} has unknown property '{key}'{log_descriptor}", tabs=tabs)

        # Set the instance's attributes to the parsed data, where the key is the attribute name
        if not set_attrs:
            return parsed_data
        for key, value in parsed_data.items():
            setattr(self, key, value)

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
    def get_from_asset_path(cls, asset_path: str, log_tabs: int = 1) -> str:
        """
        Returns the ID of an object from its asset path.
        If the object does not exist, it creates a new instance by parsing the asset file.
        """
        obj_id = path_to_id(asset_path)
        obj = cls.get_from_id(obj_id)
        if obj is None:
            file_path = asset_path_to_file_path(asset_path)
            log(f"Parsing {cls.__name__} {obj_id} from {file_path}", tabs=log_tabs)
            obj_data = get_json_data(file_path)[0]
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