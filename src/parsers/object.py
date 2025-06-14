
import json
import os

class Object: #generic object that all classes extend
    objects = dict()  # Dictionary to hold all object instances
    localization_table_id = None  # Class variable to hold the localization table ID

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

    @classmethod
    def get_from_id(cls, id, create_if_missing=False):
        if id not in cls.objects:
            if create_if_missing:
                return cls(id)
            else:
                return None
        else:
            return cls.objects[id]
        
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
    def objects_to_dict(cls):
        """
        Returns a dictionary representation of all objects
        """
        new_dict = dict()
        new_dict['localization_table_id'] = cls.localization_table_id
        new_dict['objects'] = {obj_id: obj.to_dict() for obj_id, obj in cls.objects.items()}
        
        return new_dict
    
    @classmethod
    def to_json(cls):
        """
        Returns a JSON string representation of all objects.
        """
        return json.dumps(cls.objects_to_dict(), indent=4, ensure_ascii=False)
    
    @classmethod
    def to_file(cls):
        file_path = os.path.join(os.getenv('OUTPUT_PATH'), f'{cls.__name__}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cls.to_json())