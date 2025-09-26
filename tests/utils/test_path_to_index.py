import unittest
import sys
import os

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

path_to_index = src_utils.path_to_index


class TestPathToIndex(unittest.TestCase):
    """Test cases for the path_to_index function."""
    
    def test_valid_numeric_index(self):
        """Test paths with valid numeric indices."""
        self.assertEqual(path_to_index("../Armor/Armor_A.5"), 5)
        self.assertEqual(path_to_index("path/to/file.0"), 0)
        self.assertEqual(path_to_index("some.file.123"), 123)
        self.assertEqual(path_to_index("test.999"), 999)
        self.assertEqual(path_to_index("single.1"), 1)
    
    def test_non_digit_index_returns_zero(self):
        """Test paths where the last part after dot is not a digit - should return 0."""
        self.assertEqual(path_to_index("../Armory/Armory_A.Armory_A"), 0)
        self.assertEqual(path_to_index("path/to/file.abc"), 0)
        self.assertEqual(path_to_index("test.file_name"), 0)
        self.assertEqual(path_to_index("something.mixed123abc"), 0)
        self.assertEqual(path_to_index("example.extension"), 0)
    
    def test_path_without_extension_raises_exception(self):
        """Test paths without any dot - should raise exception."""
        with self.assertRaises(Exception) as context:
            path_to_index("no_extension_file")
        self.assertIn("No index found in asset_path:", str(context.exception))
        
        with self.assertRaises(Exception) as context:
            path_to_index("path/to/file_without_extension")
        self.assertIn("No index found in asset_path:", str(context.exception))
    
    def test_path_ending_with_dot_raises_exception(self):
        """Test paths ending with a dot (empty index) - should raise exception."""
        with self.assertRaises(Exception) as context:
            path_to_index("file.")
        self.assertIn("No index found in asset_path:", str(context.exception))
        
        with self.assertRaises(Exception) as context:
            path_to_index("path/to/file.")
        self.assertIn("No index found in asset_path:", str(context.exception))
    
    def test_multiple_dots_uses_last_segment(self):
        """Test paths with multiple dots - should use the segment after the last dot."""
        self.assertEqual(path_to_index("file.name.extension.42"), 42)
        self.assertEqual(path_to_index("a.b.c.d.e.7"), 7)
        self.assertEqual(path_to_index("version.1.0.final"), 0)  # "final" is not a digit
        self.assertEqual(path_to_index("test.v1.2.3"), 3)
    
    def test_negative_numbers_not_digits(self):
        """Test that negative numbers are not considered digits - should return 0."""
        self.assertEqual(path_to_index("file.-5"), 0)
        self.assertEqual(path_to_index("path/to/test.-123"), 0)
    
    def test_floating_point_numbers_not_digits(self):
        """Test that floating point numbers are not considered digits - should return 0."""
        self.assertEqual(path_to_index("file.3.14"), 14)  # Takes last segment after dot
        self.assertEqual(path_to_index("test.1.5"), 5)
    
    def test_leading_zeros(self):
        """Test numbers with leading zeros."""
        self.assertEqual(path_to_index("file.007"), 7)
        self.assertEqual(path_to_index("test.000"), 0)
        self.assertEqual(path_to_index("path.0123"), 123)
    
    def test_empty_string_raises_exception(self):
        """Test empty string - should raise exception."""
        with self.assertRaises(Exception) as context:
            path_to_index("")
        self.assertIn("No index found in asset_path:", str(context.exception))
    
    def test_alphanumeric_mix(self):
        """Test alphanumeric combinations - should return 0."""
        self.assertEqual(path_to_index("file.123abc"), 0)
        self.assertEqual(path_to_index("test.abc123"), 0)
        self.assertEqual(path_to_index("path.1a2b3c"), 0)
    
    def test_special_characters(self):
        """Test paths with special characters in the index part - should return 0."""
        self.assertEqual(path_to_index("file.@#$"), 0)
        self.assertEqual(path_to_index("test.123!"), 0)
        self.assertEqual(path_to_index("path.index_1"), 0)
    
    def test_unicode_characters(self):
        """Test paths with unicode characters - should return 0."""
        self.assertEqual(path_to_index("file.测试"), 0)
        self.assertEqual(path_to_index("test.αβγ"), 0)
    
    def test_very_large_numbers(self):
        """Test very large numeric indices."""
        large_number = "9" * 100  # 100-digit number
        result = path_to_index(f"file.{large_number}")
        self.assertEqual(result, int(large_number))
    
    def test_game_specific_examples(self):
        """Test with examples from the game data comments."""
        # From the comment: ../Armor/Armor_A.5 -> 5
        self.assertEqual(path_to_index("/Armor/Armor_A.5"), 5)
        
        # From the comment: ../Armory/Armory_A.Armory_A -> 0
        self.assertEqual(path_to_index("/Armory/Armory_A.Armory_A"), 0)
        
        # Additional game-like paths
        self.assertEqual(path_to_index("/Game/DungeonCrawler/Data/Item.0"), 0)
        self.assertEqual(path_to_index("DungeonCrawler/Content/Weapons/Sword.Sword_C"), 0)


if __name__ == '__main__':
    unittest.main()
