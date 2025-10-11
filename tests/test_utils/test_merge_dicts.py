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

merge_dicts = src_utils.merge_dicts


class TestMergeDicts(unittest.TestCase):
    """Test cases for the merge_dicts function."""
    
    def test_none_base_dict(self):
        """Test merging when base dict is None."""
        base = None
        overlay = {"key": "value"}
        expected = {"key": "value"}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_empty_base_dict(self):
        """Test merging when base dict is empty."""
        base = {}
        overlay = {"key": "value", "number": 42}
        expected = {"key": "value", "number": 42}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_none_overlay_dict(self):
        """Test merging when overlay dict is None."""
        base = {"key": "value", "number": 42}
        overlay = None
        expected = {"key": "value", "number": 42}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_empty_overlay_dict(self):
        """Test merging when overlay dict is empty."""
        base = {"key": "value", "number": 42}
        overlay = {}
        expected = {"key": "value", "number": 42}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_both_empty_dicts(self):
        """Test merging when both dicts are empty."""
        base = {}
        overlay = {}
        expected = {}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_simple_merge_no_conflicts(self):
        """Test simple merge with no key conflicts."""
        base = {"a": 1, "b": 2}
        overlay = {"c": 3, "d": 4}
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_overlay_overwrites_base(self):
        """Test that overlay values overwrite base values."""
        base = {"a": 1, "b": 2, "c": 3}
        overlay = {"b": 20, "c": 30}
        expected = {"a": 1, "b": 20, "c": 30}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_nested_dict_merge(self):
        """Test recursive merging of nested dictionaries."""
        base = {
            "user": {
                "name": "John",
                "age": 30
            },
            "settings": {
                "theme": "light"
            }
        }
        overlay = {
            "user": {
                "email": "john@example.com",
                "age": 31
            },
            "settings": {
                "notifications": True
            }
        }
        expected = {
            "user": {
                "name": "John",
                "age": 31,
                "email": "john@example.com"
            },
            "settings": {
                "theme": "light",
                "notifications": True
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_deep_nested_dict_merge(self):
        """Test merging deeply nested dictionaries."""
        base = {
            "level1": {
                "level2": {
                    "level3": {
                        "keep": "original",
                        "update": "old_value"
                    }
                }
            }
        }
        overlay = {
            "level1": {
                "level2": {
                    "level3": {
                        "update": "new_value",
                        "add": "new_item"
                    }
                }
            }
        }
        expected = {
            "level1": {
                "level2": {
                    "level3": {
                        "keep": "original",
                        "update": "new_value",
                        "add": "new_item"
                    }
                }
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_type_mismatch_raises_error(self):
        """Test that type mismatches raise TypeError."""
        base = {"key": "string_value"}
        overlay = {"key": 42}  # Different type
        
        with self.assertRaises(TypeError) as context:
            merge_dicts(base, overlay)
        
        self.assertIn("Type mismatch for key 'key'", str(context.exception))
        self.assertIn("<class 'int'> vs <class 'str'>", str(context.exception))
    
    def test_type_mismatch_nested_raises_error(self):
        """Test that type mismatches in nested dicts raise TypeError."""
        base = {
            "user": {
                "id": "string_id"
            }
        }
        overlay = {
            "user": {
                "id": 123  # Different type
            }
        }
        
        with self.assertRaises(TypeError) as context:
            merge_dicts(base, overlay)
        
        self.assertIn("Type mismatch for key 'id'", str(context.exception))
    
    def test_none_values_in_overlay_ignored(self):
        """Test that None values in overlay are ignored."""
        base = {"keep": "value", "update": "old"}
        overlay = {"ignore": None, "update": "new", "also_ignore": None}
        expected = {"keep": "value", "update": "new"}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_empty_list_values_in_overlay_ignored(self):
        """Test that empty list values in overlay are ignored."""
        base = {"keep": "value", "update": "old"}
        overlay = {"ignore": [], "update": "new", "also_ignore": []}
        expected = {"keep": "value", "update": "new"}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_non_empty_list_values_preserved(self):
        """Test that non-empty list values are preserved."""
        base = {"numbers": [1, 2]}
        overlay = {"numbers": [3, 4, 5], "letters": ["a", "b"]}
        expected = {"numbers": [3, 4, 5], "letters": ["a", "b"]}
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_dict_vs_non_dict_raises_error(self):
        """Test that when base has dict and overlay has non-dict, TypeError is raised."""
        base = {
            "config": {
                "nested": "value"
            }
        }
        overlay = {
            "config": "simple_string"
        }
        
        with self.assertRaises(TypeError) as context:
            merge_dicts(base, overlay)
        
        self.assertIn("Type mismatch for key 'config'", str(context.exception))
        self.assertIn("<class 'str'> vs <class 'dict'>", str(context.exception))
    
    def test_non_dict_vs_dict_raises_error(self):
        """Test that when base has non-dict and overlay has dict, TypeError is raised."""
        base = {
            "config": "simple_string"
        }
        overlay = {
            "config": {
                "nested": "value"
            }
        }
        
        with self.assertRaises(TypeError) as context:
            merge_dicts(base, overlay)
        
        self.assertIn("Type mismatch for key 'config'", str(context.exception))
        self.assertIn("<class 'dict'> vs <class 'str'>", str(context.exception))
    
    def test_overlay_with_base_none_no_type_error(self):
        """Test that overlay can set value when base value is None."""
        base = {
            "config": None,
            "other": "keep"
        }
        overlay = {
            "config": {
                "nested": "value"
            }
        }
        expected = {
            "other": "keep",
            "config": {
                "nested": "value"
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_base_with_overlay_none_preserved(self):
        """Test that base value is preserved when overlay value is None."""
        base = {
            "config": {
                "nested": "value"
            },
            "other": "keep"
        }
        overlay = {
            "config": None  # This should be ignored
        }
        expected = {
            "config": {
                "nested": "value"
            },
            "other": "keep"
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_remove_blank_values_integration(self):
        """Test that remove_blank_values is called on the result."""
        base = {"keep": "value"}
        overlay = {
            "add": "new_value",
            "blank_string": "",
            "blank_list": [],
            "blank_dict": {},
            "blank_none": None,
            "nested": {
                "keep_nested": "value",
                "remove_nested": None
            }
        }
        expected = {
            "keep": "value",
            "add": "new_value",
            "nested": {
                "keep_nested": "value"
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_game_data_merge_example(self):
        """Test with game-specific data structure."""
        base = {
            "weapon": {
                "name": "Sword",
                "damage": 100,
                "stats": {
                    "strength": 50,
                    "speed": 30
                }
            },
            "character": {
                "level": 10
            }
        }
        overlay = {
            "weapon": {
                "damage": 120,  # Update damage
                "stats": {
                    "strength": 60,  # Update strength
                    "magic": 20     # Add magic
                },
                "enchantment": "fire"  # Add enchantment
            },
            "inventory": {
                "potions": 5
            }
        }
        expected = {
            "weapon": {
                "name": "Sword",
                "damage": 120,
                "stats": {
                    "strength": 60,
                    "speed": 30,
                    "magic": 20
                },
                "enchantment": "fire"
            },
            "character": {
                "level": 10
            },
            "inventory": {
                "potions": 5
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_complex_type_handling(self):
        """Test merging with various data types."""
        base = {
            "string": "base_string",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {
                "inner_string": "inner_base"
            }
        }
        overlay = {
            "string": "overlay_string",
            "float": 3.14,
            "list": [4, 5, 6],  # This will replace the base list
            "nested": {
                "inner_number": 99
            }
        }
        expected = {
            "string": "overlay_string",
            "number": 42,
            "boolean": True,
            "float": 3.14,
            "list": [4, 5, 6],
            "nested": {
                "inner_string": "inner_base",
                "inner_number": 99
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_original_dicts_not_modified(self):
        """Test that original dictionaries are not modified."""
        base_original = {"a": 1, "nested": {"x": 10}}
        overlay_original = {"b": 2, "nested": {"y": 20}}
        
        base_copy = {"a": 1, "nested": {"x": 10}}
        overlay_copy = {"b": 2, "nested": {"y": 20}}
        
        result = merge_dicts(base_original, overlay_original)
        
        # Original dicts should be unchanged
        self.assertEqual(base_original, base_copy)
        self.assertEqual(overlay_original, overlay_copy)
        
        # Result should be merged
        expected = {"a": 1, "b": 2, "nested": {"x": 10, "y": 20}}
        self.assertEqual(result, expected)
    
    def test_falsy_values_preserved(self):
        """Test that falsy but valid values are preserved."""
        base = {"keep": "value"}
        overlay = {
            "zero": 0,
            "false": False,
            "empty_tuple": (),
            "empty_string": "",  # This should be removed by remove_blank_values
            "empty_list": []     # This should be removed by remove_blank_values
        }
        expected = {
            "keep": "value",
            "zero": 0,
            "false": False,
            "empty_tuple": ()
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)
    
    def test_nested_empty_removal_cascade(self):
        """Test that nested structures are properly cleaned up."""
        base = {"keep": "value"}
        overlay = {
            "remove_entirely": {
                "all_blank": None,
                "nested_blank": {
                    "deep_blank": ""
                }
            },
            "partial_keep": {
                "keep_this": "value",
                "remove_this": None
            }
        }
        expected = {
            "keep": "value",
            "partial_keep": {
                "keep_this": "value"
            }
        }
        result = merge_dicts(base, overlay)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()