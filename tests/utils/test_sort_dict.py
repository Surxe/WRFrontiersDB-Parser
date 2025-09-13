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

sort_dict = src_utils.sort_dict


class TestSortDict(unittest.TestCase):
    """Test cases for the sort_dict function."""
    
    def test_empty_dict(self):
        """Test sorting an empty dictionary."""
        result = sort_dict({})
        expected = {}
        self.assertEqual(result, expected)
    
    def test_single_level_dict(self):
        """Test sorting a single-level dictionary."""
        input_dict = {"c": 3, "a": 1, "b": 2}
        result = sort_dict(input_dict)
        expected = {"a": 1, "b": 2, "c": 3}
        self.assertEqual(result, expected)
        # Verify order is maintained
        self.assertEqual(list(result.keys()), ["a", "b", "c"])
    
    def test_nested_dict_all_levels(self):
        """Test sorting nested dictionaries at all levels (default behavior)."""
        input_dict = {
            "z": {"y": 1, "x": 2},
            "a": {"c": 3, "b": 4},
            "m": {"n": {"q": 5, "p": 6}}
        }
        result = sort_dict(input_dict)
        expected = {
            "a": {"b": 4, "c": 3},
            "m": {"n": {"p": 6, "q": 5}},
            "z": {"x": 2, "y": 1}
        }
        self.assertEqual(result, expected)
        # Verify top-level order
        self.assertEqual(list(result.keys()), ["a", "m", "z"])
        # Verify nested order
        self.assertEqual(list(result["a"].keys()), ["b", "c"])
        self.assertEqual(list(result["m"]["n"].keys()), ["p", "q"])
    
    def test_num_levels_zero(self):
        """Test with num_levels=0 (no sorting)."""
        input_dict = {"c": 3, "a": 1, "b": 2}
        result = sort_dict(input_dict, num_levels=0)
        # Should return the original dict unchanged
        self.assertEqual(result, input_dict)
        # Order should be preserved from input
        self.assertEqual(list(result.keys()), ["c", "a", "b"])
    
    def test_num_levels_one(self):
        """Test with num_levels=1 (sort only top level)."""
        input_dict = {
            "z": {"y": 1, "x": 2},
            "a": {"c": 3, "b": 4}
        }
        result = sort_dict(input_dict, num_levels=1)
        expected = {
            "a": {"c": 3, "b": 4},  # nested dict not sorted
            "z": {"y": 1, "x": 2}   # nested dict not sorted
        }
        self.assertEqual(result, expected)
        # Top level should be sorted
        self.assertEqual(list(result.keys()), ["a", "z"])
        # Nested levels should maintain original order
        self.assertEqual(list(result["a"].keys()), ["c", "b"])
        self.assertEqual(list(result["z"].keys()), ["y", "x"])
    
    def test_num_levels_two(self):
        """Test with num_levels=2 (sort first two levels)."""
        input_dict = {
            "z": {
                "y": {"d": 1, "c": 2},
                "x": {"b": 3, "a": 4}
            },
            "a": {
                "c": {"f": 5, "e": 6},
                "b": {"h": 7, "g": 8}
            }
        }
        result = sort_dict(input_dict, num_levels=2)
        expected = {
            "a": {
                "b": {"h": 7, "g": 8},  # third level not sorted
                "c": {"f": 5, "e": 6}   # third level not sorted
            },
            "z": {
                "x": {"b": 3, "a": 4},  # third level not sorted
                "y": {"d": 1, "c": 2}   # third level not sorted
            }
        }
        self.assertEqual(result, expected)
        # First two levels should be sorted
        self.assertEqual(list(result.keys()), ["a", "z"])
        self.assertEqual(list(result["a"].keys()), ["b", "c"])
        # Third level should maintain original order
        self.assertEqual(list(result["a"]["b"].keys()), ["h", "g"])
    
    def test_non_dict_input(self):
        """Test with non-dictionary input."""
        # Should return the input unchanged
        self.assertEqual(sort_dict("string"), "string")
        self.assertEqual(sort_dict(123), 123)
        self.assertEqual(sort_dict([1, 2, 3]), [1, 2, 3])
        self.assertEqual(sort_dict(None), None)
    
    def test_dict_with_non_dict_values(self):
        """Test dictionary containing non-dictionary values."""
        input_dict = {
            "c": [3, 2, 1],
            "a": "hello",
            "b": {"nested": "value"}
        }
        result = sort_dict(input_dict)
        expected = {
            "a": "hello",
            "b": {"nested": "value"},
            "c": [3, 2, 1]
        }
        self.assertEqual(result, expected)
        self.assertEqual(list(result.keys()), ["a", "b", "c"])
    
    def test_mixed_key_types(self):
        """Test dictionary with mixed key types that can be sorted together."""
        # Use only string keys since Python 3 doesn't allow comparison between str and int
        input_dict = {"3": "three", "a": "letter", "1": "one", "z": "last"}
        result = sort_dict(input_dict)
        # Keys should be sorted according to Python's default sorting
        expected_keys = sorted(input_dict.keys())
        self.assertEqual(list(result.keys()), expected_keys)
        
    def test_numeric_keys(self):
        """Test dictionary with numeric keys."""
        input_dict = {3: "three", 1: "one", 2: "two"}
        result = sort_dict(input_dict)
        expected_keys = [1, 2, 3]
        self.assertEqual(list(result.keys()), expected_keys)
    
    def test_num_levels_negative_one_explicit(self):
        """Test with num_levels=-1 explicitly (should sort all levels)."""
        input_dict = {
            "z": {"y": 1, "x": 2},
            "a": {"c": 3, "b": 4}
        }
        result = sort_dict(input_dict, num_levels=-1)
        expected = {
            "a": {"b": 4, "c": 3},
            "z": {"x": 2, "y": 1}
        }
        self.assertEqual(result, expected)
    
    def test_deeply_nested_dict(self):
        """Test with deeply nested dictionary structure."""
        input_dict = {
            "level1_z": {
                "level2_y": {
                    "level3_x": {
                        "level4_w": {"d": 1, "c": 2, "a": 3}
                    }
                }
            },
            "level1_a": {
                "level2_b": {
                    "level3_c": {
                        "level4_d": {"z": 4, "y": 5, "x": 6}
                    }
                }
            }
        }
        result = sort_dict(input_dict)
        
        # Check that all levels are sorted
        self.assertEqual(list(result.keys()), ["level1_a", "level1_z"])
        
        # Navigate to deepest level and check sorting
        deepest_dict_1 = result["level1_a"]["level2_b"]["level3_c"]["level4_d"]
        self.assertEqual(list(deepest_dict_1.keys()), ["x", "y", "z"])
        
        deepest_dict_2 = result["level1_z"]["level2_y"]["level3_x"]["level4_w"]
        self.assertEqual(list(deepest_dict_2.keys()), ["a", "c", "d"])
    
    def test_preserves_original_dict(self):
        """Test that the original dictionary is not modified."""
        original_dict = {"c": 3, "a": 1, "b": 2}
        original_keys = list(original_dict.keys())
        
        result = sort_dict(original_dict)
        
        # Original dict should be unchanged
        self.assertEqual(list(original_dict.keys()), original_keys)
        # Result should be different
        self.assertNotEqual(list(result.keys()), original_keys)
    
    def test_large_num_levels(self):
        """Test with num_levels larger than actual depth."""
        input_dict = {"b": {"a": 1}, "a": {"b": 2}}
        result = sort_dict(input_dict, num_levels=10)
        expected = {"a": {"b": 2}, "b": {"a": 1}}
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
