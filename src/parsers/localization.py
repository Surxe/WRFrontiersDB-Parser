# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from utils import PARAMS, log, get_json_data

from parsers.object import Object

class Localization(Object):
    objects = dict()  # Dictionary to hold all Localization instances

    def _parse(self):
        pass

    def _to_file(self):
        """
        Saves the localization data to a JSON file in the output path.
        """
        if not isinstance(self.source_data, dict):
            log(f"Localization source data is not a dictionary: {type(self.source_data)}", tabs=1)
            return
        
        file_path = os.path.join(PARAMS.output_path, f'Localization\{self.id}.json')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.source_data, f, indent=4, ensure_ascii=False)

    def _localize(self, table_namespace, key):
        """
        Localizes a given key using the localization table namespace.
        """
        
        return self.source_data[table_namespace][key]

def parse_localizations():
    localization_source_path = os.path.join(PARAMS.export_path, r"WRFrontiers\Content\Localization\Game")

    for dir_name in os.listdir(localization_source_path):
        if not os.path.isdir(os.path.join(localization_source_path, dir_name)):
            continue

        lang_code = dir_name
        dir_path = os.path.join(localization_source_path, dir_name)
        
        for file_name in os.listdir(dir_path):
            if not file_name.endswith('.json'):
                continue

            file_path = os.path.join(dir_path, file_name)
            source_data = get_json_data(file_path)
            if not isinstance(source_data, dict):
                log(f"Localization source data is not a dictionary: {type(source_data)}", tabs=0)
                continue

            log(f"Parsing localization for language: {lang_code} from file: {file_path}", tabs=1)
            localization = Localization(lang_code, source_data)
            localization._to_file()

if __name__ == "__main__":
    parse_localizations()