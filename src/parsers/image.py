# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import asset_path_to_file_path, PARAMS

class Image():
    image_paths = dict()  # Dictionary to hold all Image instances

    def __init__(self, image_path: str):
        if not isinstance(image_path, str):
            raise TypeError("Image path must be a string.")
        if image_path not in self.image_paths:
            self.image_paths[image_path] = True

def parse_image_asset_path(data: dict) -> str:
    asset_path = data["AssetPathName"]
    export_plus_file_path = asset_path_to_file_path(asset_path)
    image_path_generic = export_plus_file_path.split(PARAMS.export_path + "\\\\")[1].replace("\\", "/")
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
    
    return {
        "image_path": image_path,
        "tint_hex": tint_hex
    }