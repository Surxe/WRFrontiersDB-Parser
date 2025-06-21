
# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import PARAMS, path_to_id, asset_path_to_file_path, get_json_data, log, parse_localization

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