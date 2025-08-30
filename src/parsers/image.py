# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import asset_path_to_file_path, PARAMS

import json

class Image():
    image_paths = dict()  # Dictionary to hold all Image instances

    def __init__(self, image_path: str):
        if not isinstance(image_path, str):
            raise TypeError("Image path must be a string.")
        if image_path not in self.image_paths:
            self.image_paths[image_path] = True

    @classmethod
    def to_file(cls):
        # Write json file of image_paths to output
        output_path = os.path.join(PARAMS.output_path, f"{cls.__name__}.json")
        with open(output_path, 'w') as f:
            json.dump(list(cls.image_paths.keys()), f, indent=4)


def parse_image_asset_path(data: dict) -> str:
    if data is None:
        return
    if "AssetPathName" in data:
        asset_path = data["AssetPathName"]
    elif "ObjectPath" in data:
        asset_path = data["ObjectPath"]
    else:
        raise ValueError("Data must contain 'AssetPathName' or 'ObjectPath'.")
    export_plus_file_path = asset_path_to_file_path(asset_path)
    image_path_generic = export_plus_file_path.split(PARAMS.export_path)[1].split(".")[0] # #<export_path>\\<file_path>\\<image_name>.json -> <file_path>/<image_name>
    Image(image_path_generic)  # Register the image path
    return image_path_generic

def parse_badge_visual_info(data: dict):
    """
    Parses the BadgeVisualInfo structure from the given data.
    """
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary.")
    
    image_path = None
    if "Image" in data and "AssetPathName" in data["Image"]:
        image_path = parse_image_asset_path(data["Image"])
        
    tint_hex = None
    if 'TintColor' in data and 'Hex' in data["TintColor"]:  
        tint_hex = data["TintColor"]["Hex"]

    returned_data = dict()
    returned_data["image_path"] = image_path
    if tint_hex is not None:
        returned_data["tint_hex"] = tint_hex
    
    return returned_data