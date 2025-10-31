# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import OPTIONS, path_to_id, asset_path_to_file_path_and_index, get_json_data, logger, merge_dicts, asset_path_to_data, process_key_to_parser_function, sort_dict

import json

class ParseObject: #generic object that all classes extend
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

    def _process_key_to_parser_function(self, key_to_parser_function_map, data, log_descriptor="", set_attrs=True, default_configuration={}):
        """
        Wrapper method that calls the utility function with self as the object.
        """
        return process_key_to_parser_function(
            key_to_parser_function_map=key_to_parser_function_map,
            data=data,
            obj=self,
            log_descriptor=log_descriptor,
            set_attrs=set_attrs,
            default_configuration=default_configuration
        )

    def _parse_from_data(source_data: dict):
        raise NotImplementedError("Subclasses must implement _parse_from_data to use _parse_and_merge_template()")

    def _parse_and_merge_template(self, template: dict):
        """
        Recursively parse and merge template ability data.
        """
        asset_path = template["ObjectPath"]
        template_data = asset_path_to_data(asset_path)
        base_template_data = {}
        if template_data and "Template" in template_data:
            base_template_data = self._parse_and_merge_template(template_data["Template"])
        parsed_template_data = self._parse_from_data(template_data) if template_data else {}
        return merge_dicts(base_template_data, parsed_template_data)

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
    def get_from_asset_path(cls, asset_path: str, sub_index=True, create_if_missing=True) -> str:
        """
        Returns the ID of an object from its asset path.
        If the object does not exist, it creates a new instance by parsing the asset file.
        sub_index: Whether to use the sub-index when parsing the asset file.
        """
        obj_id = path_to_id(asset_path)
        obj = cls.get_from_id(obj_id)
        if obj is None and create_if_missing:
            file_path, index = asset_path_to_file_path_and_index(asset_path)
            logger.debug(f"Parsing {cls.__name__} {obj_id} from {file_path} . {index}")
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

        new_dict = sort_dict({obj_id: obj.to_dict() for obj_id, obj in cls.objects.items()}, 1) #sort the root layer only

        return new_dict
    
    @classmethod
    def to_json(cls):
        """
        Returns a JSON string representation of all objects.
        """
        return json.dumps(cls.objects_to_dict(), indent=4, ensure_ascii=False)
    
    @classmethod
    def to_file(cls):
        file_path = os.path.join(OPTIONS.output_dir, f'{cls.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cls.to_json())