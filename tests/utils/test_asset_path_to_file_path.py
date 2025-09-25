import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

from utils import normalize_path

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

asset_path_to_file_path = src_utils.asset_path_to_file_path


class TestAssetPathToFilePath(unittest.TestCase):
    """Test cases for the asset_path_to_file_path function."""
    
    def setUp(self):
        """Set up test fixtures with mock PARAMS."""
        # Mock the PARAMS object that the function depends on
        self.mock_params = Mock()
        self.mock_params.game_name = "DungeonCrawler"
        self.mock_params.export_path = "F:\\TestExports"
        
        # Set the PARAMS in the utils module directly
        src_utils.PARAMS = self.mock_params
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up the PARAMS if it exists
        if hasattr(src_utils, 'PARAMS'):
            delattr(src_utils, 'PARAMS')
    
    def test_game_path_conversion(self):
        """Test conversion of /Game/ paths to file paths."""
        # Test basic Game path
        asset_path = "/Game/DungeonCrawler/Data/Item.0"
        expected = normalize_path("F:\\TestExports\\DungeonCrawler\\Content\\DungeonCrawler\\Data\\Item.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
        
        # Test complex Game path
        asset_path = "/Game/DungeonCrawler/Maps/Dungeon/Modules/Crypt/Edge/Armory/Armory_A.Armory_A"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\DungeonCrawler\\Maps\\Dungeon\\Modules\\Crypt\\Edge\\Armory\\Armory_A.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_direct_content_path(self):
        """Test paths that already start with DungeonCrawler/Content."""
        asset_path = "DungeonCrawler/Content/DungeonCrawler/ActorStatus/Buff/AbyssalFlame/GE_AbyssalFlame.0"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\DungeonCrawler\\ActorStatus\\Buff\\AbyssalFlame\\GE_AbyssalFlame.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_blueprint_generated_class_format(self):
        """Test BlueprintGeneratedClass format with single quotes."""
        asset_path = "BlueprintGeneratedClass'/Game/Sparrow/Weapons/BP_Buff_A.BP_Buff_A_C'"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Sparrow\\Weapons\\BP_Buff_A.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
        
        # Test with different quote content
        asset_path = "SomeClass'/Game/Items/Weapon.Weapon_Data'"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Items\\Weapon.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_index_removal(self):
        """Test that indices are properly removed from file paths."""
        # Numeric index
        asset_path = "/Game/Items/Weapon.123"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Items\\Weapon.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
        
        # Named index
        asset_path = "/Game/Items/Armor.Armor_Heavy"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Items\\Armor.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
        
        # Multiple dots
        asset_path = "/Game/Items/Complex.Name.With.Dots.5"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Items\\Complex.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_different_game_names(self):
        """Test with different game names."""
        # Change game name
        self.mock_params.game_name = "TestGame"
        
        asset_path = "/Game/TestContent/Data/Item.0"
        expected = os.path.normpath("F:\\TestExports\\TestGame\\Content\\TestContent\\Data\\Item.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_different_export_paths(self):
        """Test with different export paths."""
        # Change export path
        self.mock_params.export_path = "C:\\GameExports"
        
        asset_path = "/Game/Data/Test.0"
        expected = os.path.normpath("C:\\GameExports\\DungeonCrawler\\Content\\Data\\Test.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_path_normalization(self):
        """Test that paths are properly normalized."""
        # Test with forward slashes in export path
        self.mock_params.export_path = "F:/TestExports"
        
        asset_path = "/Game/Data/Test.0"
        result = asset_path_to_file_path(asset_path)
        
        # Result should be properly normalized for the OS
        self.assertIn("Test.json", result)
        self.assertTrue(os.path.isabs(result))
    
    def test_no_quotes_in_path(self):
        """Test paths without quotes (should not be affected by quote processing)."""
        asset_path = "/Game/Regular/Path.0"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Regular\\Path.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_single_quote_in_path(self):
        """Test paths with only one quote (should not trigger quote processing)."""
        asset_path = "/Game/Path'With/Single/Quote.0"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\Path'With\\Single\\Quote.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_multiple_quotes_but_not_two(self):
        """Test paths with 3+ quotes (should not trigger quote processing)."""
        asset_path = "Class'Path'With'Multiple'Quotes.0"
        # Should not process quotes since count != 2, but still processes /Game/ replacement
        expected = os.path.normpath("F:\\TestExports\\Class'Path'With'Multiple'Quotes.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_game_specific_examples_from_comments(self):
        """Test with the specific examples mentioned in the function comments."""
        # ObjectPath example
        asset_path = "DungeonCrawler/Content/DungeonCrawler/ActorStatus/Buff/AbyssalFlame/GE_AbyssalFlame.0"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\DungeonCrawler\\ActorStatus\\Buff\\AbyssalFlame\\GE_AbyssalFlame.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
        
        # asset_path_name (V2) example
        asset_path = "/Game/DungeonCrawler/Maps/Dungeon/Modules/Crypt/Edge/Armory/Armory_A.Armory_A"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\DungeonCrawler\\Maps\\Dungeon\\Modules\\Crypt\\Edge\\Armory\\Armory_A.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
    
    def test_edge_cases(self):
        """Test various edge cases."""
        # Empty path after /Game/
        asset_path = "/Game/.0"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)
        
        # Path without extension
        asset_path = "/Game/NoExtension"
        expected = os.path.normpath("F:\\TestExports\\DungeonCrawler\\Content\\NoExtension.json")
        result = asset_path_to_file_path(asset_path)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
