# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import asset_path_to_data

class ModuleParser:
    def __init__(self, asset_path: str):
        self.asset_path = asset_path
        self.data = asset_path_to_data(asset_path)

def parse_modules():
    # Example usage
    asset_path = "/Game/Sparrow/Modules/Abilities/BP_Ability_ArmorShield.BP_Ability_ArmorShield_C"
    parser = ModuleParser(asset_path)
    print(parser.data)

if __name__ == "__main__":
    parse_modules()