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

remove_blank_values = src_utils.remove_blank_values


class TestRemoveBlankValues(unittest.TestCase):
    """Test cases for the remove_blank_values function."""
    
    def test_non_dict_input_returned_unchanged(self):
        """Test that non-dict inputs are returned unchanged."""
        self.assertEqual(remove_blank_values("string"), "string")
        self.assertEqual(remove_blank_values(123), 123)
        self.assertEqual(remove_blank_values([1, 2, 3]), [1, 2, 3])
        self.assertEqual(remove_blank_values(None), None)
        self.assertEqual(remove_blank_values(True), True)
    
    def test_empty_dict(self):
        """Test empty dictionary handling."""
        self.assertEqual(remove_blank_values({}), {})
    
    def test_input_is_empty_value(self):
        """Test when the input itself is an empty value."""
        self.assertEqual(remove_blank_values({}), {})
        self.assertEqual(remove_blank_values([]), [])
        self.assertEqual(remove_blank_values(""), "")
        self.assertEqual(remove_blank_values(None), None)
    
    def test_dict_with_no_blank_values(self):
        """Test dictionary with no blank values remains unchanged."""
        input_dict = {
            "name": "test",
            "value": 42,
            "active": True,
            "data": [1, 2, 3],
            "config": {"setting": "value"}
        }
        expected = input_dict.copy()
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_remove_none_values(self):
        """Test removal of None values."""
        input_dict = {
            "keep": "value",
            "remove": None,
            "also_keep": 42
        }
        expected = {
            "keep": "value",
            "also_keep": 42
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_remove_empty_string_values(self):
        """Test removal of empty string values."""
        input_dict = {
            "keep": "value",
            "remove": "",
            "also_keep": "non-empty"
        }
        expected = {
            "keep": "value",
            "also_keep": "non-empty"
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_remove_empty_list_values(self):
        """Test removal of empty list values."""
        input_dict = {
            "keep": [1, 2, 3],
            "remove": [],
            "also_keep": "value"
        }
        expected = {
            "keep": [1, 2, 3],
            "also_keep": "value"
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_remove_empty_dict_values(self):
        """Test removal of empty dictionary values."""
        input_dict = {
            "keep": {"nested": "value"},
            "remove": {},
            "also_keep": "value"
        }
        expected = {
            "keep": {"nested": "value"},
            "also_keep": "value"
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_remove_all_blank_types(self):
        """Test removal of all blank value types in one dict."""
        input_dict = {
            "keep1": "value",
            "remove_none": None,
            "remove_empty_string": "",
            "remove_empty_list": [],
            "remove_empty_dict": {},
            "keep2": 42,
            "keep3": [1, 2]
        }
        expected = {
            "keep1": "value",
            "keep2": 42,
            "keep3": [1, 2]
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_recursive_nested_dicts(self):
        """Test recursive processing of nested dictionaries."""
        input_dict = {
            "level1": {
                "keep": "value",
                "remove": None,
                "level2": {
                    "keep_nested": "nested_value",
                    "remove_nested": "",
                    "level3": {
                        "deep_keep": "deep_value",
                        "deep_remove": []
                    }
                }
            },
            "top_level_keep": "top_value"
        }
        expected = {
            "level1": {
                "keep": "value",
                "level2": {
                    "keep_nested": "nested_value",
                    "level3": {
                        "deep_keep": "deep_value"
                    }
                }
            },
            "top_level_keep": "top_value"
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_nested_empty_dicts_removed(self):
        """Test that nested dictionaries become empty and get removed."""
        input_dict = {
            "keep": "value",
            "remove_becomes_empty": {
                "all_blank": None,
                "also_blank": "",
                "nested_blank": {
                    "blank1": [],
                    "blank2": {}
                }
            },
            "partial_removal": {
                "keep_this": "value",
                "remove_this": None
            }
        }
        expected = {
            "keep": "value",
            "partial_removal": {
                "keep_this": "value"
            }
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_preserve_falsy_non_blank_values(self):
        """Test that falsy but non-blank values are preserved."""
        input_dict = {
            "zero": 0,
            "false": False,
            "empty_tuple": (),
            "remove_none": None,
            "remove_empty_string": "",
            "remove_empty_list": [],
            "remove_empty_dict": {}
        }
        expected = {
            "zero": 0,
            "false": False,
            "empty_tuple": ()
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_complex_nested_structure(self):
        """Test complex nested structure with mixed data types."""
        input_dict = {
            "user": {
                "name": "John",
                "email": "",  # Should be removed
                "profile": {
                    "age": 30,
                    "bio": None,  # Should be removed
                    "preferences": {
                        "theme": "dark",
                        "notifications": []  # Should be removed
                    },
                    "settings": {}  # Should be removed
                },
                "scores": [100, 95, 88]
            },
            "metadata": {
                "created": "2023-01-01",
                "updated": None,  # Should be removed
                "tags": []  # Should be removed
            }
        }
        expected = {
            "user": {
                "name": "John",
                "profile": {
                    "age": 30,
                    "preferences": {
                        "theme": "dark"
                    }
                },
                "scores": [100, 95, 88]
            },
            "metadata": {
                "created": "2023-01-01"
            }
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_game_data_structure(self):
        """Test with game-specific data structure."""
        input_dict = {
            "weapon": {
                "name": "Sword",
                "damage": 100,
                "description": "",  # Should be removed
                "stats": {
                    "strength": 50,
                    "magic": None,  # Should be removed
                    "effects": []  # Should be removed
                },
                "upgrades": {
                    "materials": ["iron", "steel"],
                    "costs": {},  # Should be removed
                    "requirements": {
                        "level": 10,
                        "quest": ""  # Should be removed
                    }
                }
            },
            "empty_category": {}  # Should be removed
        }
        expected = {
            "weapon": {
                "name": "Sword",
                "damage": 100,
                "stats": {
                    "strength": 50
                },
                "upgrades": {
                    "materials": ["iron", "steel"],
                    "requirements": {
                        "level": 10
                    }
                }
            }
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_edge_case_all_blank_dict(self):
        """Test dictionary with all blank values."""
        input_dict = {
            "blank1": None,
            "blank2": "",
            "blank3": [],
            "blank4": {}
        }
        expected = {}
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_deeply_nested_all_blank(self):
        """Test deeply nested structure with all blank values."""
        input_dict = {
            "level1": {
                "level2": {
                    "level3": {
                        "blank": None
                    }
                }
            }
        }
        expected = {}  # Now all empty dicts are properly removed
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_mixed_list_and_dict_values(self):
        """Test dictionary containing lists with various elements."""
        input_dict = {
            "valid_list": [1, "two", {"three": 3}],
            "list_with_empty_dict": [1, {}, 3],  # List itself not removed, but contains empty dict
            "empty_list": [],  # Should be removed
            "nested": {
                "items": ["a", "b", "c"],
                "empty_items": []  # Should be removed
            }
        }
        expected = {
            "valid_list": [1, "two", {"three": 3}],
            "list_with_empty_dict": [1, {}, 3],  # List preserved, function doesn't recurse into lists
            "nested": {
                "items": ["a", "b", "c"]
            }
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_cascading_empty_removal(self):
        """Test that empty dictionaries are removed in a cascading manner."""
        input_dict = {
            "level1": {
                "level2a": {
                    "level3a": {
                        "blank": None
                    },
                    "level3b": {
                        "also_blank": ""
                    }
                },
                "level2b": {
                    "keep_this": "value"
                }
            },
            "top_level": "keep_me"
        }
        expected = {
            "level1": {
                "level2b": {
                    "keep_this": "value"
                }
            },
            "top_level": "keep_me"
        }
        result = remove_blank_values(input_dict)
        self.assertEqual(result, expected)
    
    def test_original_dict_not_modified(self):
        """Test that the original dictionary is not modified."""
        original = {
            "keep": "value",
            "remove": None,
            "nested": {
                "keep_nested": "value",
                "remove_nested": ""
            }
        }
        original_copy = {
            "keep": "value",
            "remove": None,
            "nested": {
                "keep_nested": "value",
                "remove_nested": ""
            }
        }
        
        result = remove_blank_values(original)
        
        # Original should be unchanged
        self.assertEqual(original, original_copy)
        
        # Result should be different
        expected = {
            "keep": "value",
            "nested": {
                "keep_nested": "value"
            }
        }
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()