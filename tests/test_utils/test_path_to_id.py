import unittest
import sys
import os

# Set required environment variables before importing utils to prevent OPTIONS validation errors
os.environ['SHOULD_PARSE'] = 'false'  # Disable parsing to avoid requiring EXPORT_DIR and OUTPUT_DIR
os.environ.setdefault('EXPORT_DIR', '/tmp/test_export')  # Fallback if SHOULD_PARSE somehow becomes true
os.environ.setdefault('OUTPUT_DIR', '/tmp/test_output')  # Fallback if SHOULD_PARSE somehow becomes true

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

path_to_id = src_utils.path_to_id


class TestPathToId(unittest.TestCase):
    """Test cases for the path_to_id function."""
    
    def test_basic_functionality(self):
        """Test basic path to ID conversion."""
        # Basic case with numeric index
        self.assertEqual(path_to_id("path/to/file.5"), "file.5")
        self.assertEqual(path_to_id("/Game/Item.0"), "Item.0")
        self.assertEqual(path_to_id("test.123"), "test.123")
    
    def test_non_numeric_index_returns_zero(self):
        """Test paths with non-numeric indices return .0."""
        # Non-numeric indices should return 0 from path_to_index
        self.assertEqual(path_to_id("path/to/file.extension"), "file.0")
        self.assertEqual(path_to_id("/Game/Asset.Asset_Name"), "Asset.0")
        self.assertEqual(path_to_id("test.abc"), "test.0")
    
    def test_game_specific_examples(self):
        """Test with game-specific asset path examples."""
        # From the function's docstring comment
        self.assertEqual(
            path_to_id("/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropGroup/Id_LootDropGroup_GhostKing.Id_LootDropGroup_GhostKing"),
            "Id_LootDropGroup_GhostKing.0"
        )
        
        # Additional game examples
        self.assertEqual(path_to_id("../Armor/Armor_A.5"), "Armor_A.5")
        self.assertEqual(path_to_id("../Armory/Armory_A.Armory_A"), "Armory_A.0")
        self.assertEqual(path_to_id("/Game/DungeonCrawler/Data/Item.0"), "Item.0")
        self.assertEqual(path_to_id("DungeonCrawler/Content/Weapons/Sword.Sword_C"), "Sword.0")
    
    def test_multiple_dots_in_path(self):
        """Test paths with multiple dots."""
        # Should use filename before first dot and index after last dot
        self.assertEqual(path_to_id("file.name.extension.42"), "file.42")
        self.assertEqual(path_to_id("path.with.dots/test.file.7"), "test.7")
        self.assertEqual(path_to_id("a.b.c.d.e.0"), "a.0")
    
    def test_edge_cases_raise_exceptions(self):
        """Test that edge cases properly raise exceptions from underlying functions."""
        # These should raise exceptions from path_to_file_name
        with self.assertRaises(ValueError):
            path_to_id("")
        
        with self.assertRaises(ValueError):
            path_to_id(None)
        
        with self.assertRaises(ValueError):
            path_to_id(".")
        
        # These should raise exceptions from path_to_index  
        with self.assertRaises(Exception):
            path_to_id("no_extension_file")
    
    def test_format_consistency(self):
        """Test that the output format is always filename.index."""
        # Verify the format is always "{filename}.{index}"
        result = path_to_id("path/to/DA_Thing.0")
        self.assertEqual(result, "DA_Thing.0")
        self.assertIn(".", result)
        
        parts = result.split(".")
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[1].isdigit() or parts[1] == "0")


if __name__ == '__main__':
    unittest.main()
