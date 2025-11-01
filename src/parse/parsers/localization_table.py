# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject
from parsers.localization import Localization

from utils import path_to_file_name

class LocalizationTable(ParseObject):
    objects = dict()  # Dictionary to hold all LocalizationTable instances
    
    def _parse(self):
        self.table_namespace = self.source_data["StringTable"]["TableNamespace"]

def parse_localization(data: dict):
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary.")
    
    localization_key = None
    if "Key" in data:
        localization_key = data["Key"]
    
    localization_table_namespace = None
    if "TableId" in data:
        table_asset_path = data["TableId"]
        if '.' in table_asset_path:
            # If the path contains a dot, it is an asset path
            localization_table_id = LocalizationTable.get_from_asset_path(table_asset_path)
            localization_table = LocalizationTable.get_from_id(localization_table_id)
            localization_table_namespace = localization_table.table_namespace
        else:
            localization_table_namespace = path_to_file_name(data["TableId"]).split('ST_')[-1] #ST_C_Currencies -> namespace is C_Currencies

    invariant_string = None
    if "CultureInvariantString" in data:
        invariant_string = data["CultureInvariantString"]  
    
    if localization_key is not None and localization_table_namespace is not None:
        localization_obj_english = Localization.get_from_id("en")
        if localization_obj_english is None:
            localization_english = None
        else:
            localization_english = localization_obj_english.localize(localization_table_namespace, localization_key)
            if localization_english is None:
                localization_english = localization_key

        return {
            "Key": localization_key,
            "TableNamespace": localization_table_namespace,
            "en": localization_english,
        }
    elif invariant_string is not None:
        return {
            "InvariantString": invariant_string
        }
    else:
        return