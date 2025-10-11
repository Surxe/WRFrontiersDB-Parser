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

process_key_to_parser_function = src_utils.process_key_to_parser_function
ParseAction = src_utils.ParseAction
ParseTarget = src_utils.ParseTarget


class MockObject:
    """Mock object for testing attribute assignment."""
    def __init__(self):
        self.id = "mock_object_id"


class TestProcessKeyToParserFunction(unittest.TestCase):
    """Test cases for the process_key_to_parser_function function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_obj = MockObject()
        self.sample_data = {
            "SimpleKey": "simple_value",
            "CamelCaseKey": "camel_value",
            "snake_case_key": "snake_value",
            "NumberValue": 42,
            "BooleanValue": True,
            "ListValue": [1, 2, 3],
            "DictValue": {"nested": "data"},
            "Id_ColorParam[2]": "indexed_value",  # Test array index removal
        }

    def test_basic_attribute_assignment(self):
        """Test basic attribute assignment with simple parser function map."""
        key_map = {
            "SimpleKey": "value",
            "CamelCaseKey": "value",
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        # Should convert CamelCase to snake_case by default
        self.assertEqual(self.mock_obj.simple_key, "simple_value")
        self.assertEqual(self.mock_obj.camel_case_key, "camel_value")

    def test_custom_parser_function(self):
        """Test using custom parser functions."""
        def double_value(value):
            return value * 2
        
        def uppercase_value(value):
            return value.upper()
        
        key_map = {
            "NumberValue": double_value,
            "SimpleKey": uppercase_value,
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.number_value, 84)  # 42 * 2
        self.assertEqual(self.mock_obj.simple_key, "SIMPLE_VALUE")

    def test_legacy_tuple_format(self):
        """Test legacy tuple format for backwards compatibility."""
        def uppercase_value(value):
            return value.upper()
        
        key_map = {
            "SimpleKey": (uppercase_value, "custom_name"),
            "CamelCaseKey": ("value", "another_custom"),
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.custom_name, "SIMPLE_VALUE")
        self.assertEqual(self.mock_obj.another_custom, "camel_value")

    def test_dict_configuration_format(self):
        """Test new dictionary configuration format."""
        def double_value(value):
            return value * 2
        
        key_map = {
            "NumberValue": {
                'parser': double_value,
                'target': 'doubled_number'
            },
            "SimpleKey": {
                'parser': 'value',
                'target': ParseTarget.MATCH_KEY
            },
            "CamelCaseKey": {
                'parser': 'value',
                'target': ParseTarget.MATCH_KEY_SNAKE
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.doubled_number, 84)
        self.assertEqual(self.mock_obj.SimpleKey, "simple_value")  # Original key preserved
        self.assertEqual(self.mock_obj.camel_case_key, "camel_value")  # Snake case

    def test_dict_entry_action(self):
        """Test DICT_ENTRY action for storing in nested dictionaries."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'properties',
                'target': ParseTarget.MATCH_KEY
            },
            "CamelCaseKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'properties',
                'target': 'custom_camel_key'
            },
            "NumberValue": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'stats.combat',
                'target': ParseTarget.MATCH_KEY_SNAKE
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.properties["SimpleKey"], "simple_value")
        self.assertEqual(self.mock_obj.properties["custom_camel_key"], "camel_value")
        self.assertEqual(self.mock_obj.stats["combat"]["number_value"], 42)

    def test_set_attrs_false_returns_dict(self):
        """Test that setting set_attrs=False returns parsed data as dictionary."""
        key_map = {
            "SimpleKey": "value",
            "NumberValue": lambda x: x * 2,
        }
        
        result = process_key_to_parser_function(
            key_map, self.sample_data, obj=None, set_attrs=False
        )
        
        expected = {
            "simple_key": "simple_value",
            "number_value": 84
        }
        self.assertEqual(result, expected)

    def test_set_attrs_false_with_dict_entry(self):
        """Test DICT_ENTRY action with set_attrs=False."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'properties',
                'target': ParseTarget.MATCH_KEY
            },
            "NumberValue": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'stats.combat',
                'target': 'damage'
            }
        }
        
        result = process_key_to_parser_function(
            key_map, self.sample_data, obj=None, set_attrs=False
        )
        
        expected = {
            "properties": {"SimpleKey": "simple_value"},
            "stats": {"combat": {"damage": 42}}
        }
        self.assertEqual(result, expected)

    def test_default_configuration(self):
        """Test using default configuration."""
        default_config = {
            'action': ParseAction.DICT_ENTRY,
            'target_dict_path': 'default_properties',
            'target': ParseTarget.MATCH_KEY
        }
        
        key_map = {
            "SimpleKey": "value",
            "NumberValue": "value",
        }
        
        process_key_to_parser_function(
            key_map, self.sample_data, self.mock_obj, 
            default_configuration=default_config
        )
        
        self.assertEqual(self.mock_obj.default_properties["SimpleKey"], "simple_value")
        self.assertEqual(self.mock_obj.default_properties["NumberValue"], 42)

    def test_array_index_removal(self):
        """Test that array indices are removed from keys."""
        key_map = {
            "Id_ColorParam": "value",  # Should match "Id_ColorParam[2]"
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.id_color_param, "indexed_value")

    def test_none_config_skip(self):
        """Test that None configuration skips processing."""
        key_map = {
            "SimpleKey": None,
            "NumberValue": "value",
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertFalse(hasattr(self.mock_obj, "simple_key"))
        self.assertEqual(self.mock_obj.number_value, 42)

    def test_none_parsed_value_skip(self):
        """Test that None parsed values are skipped."""
        def return_none(value):
            return None
        
        key_map = {
            "SimpleKey": return_none,
            "NumberValue": "value",
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertFalse(hasattr(self.mock_obj, "simple_key"))
        self.assertEqual(self.mock_obj.number_value, 42)

    def test_unknown_key_logging(self):
        """Test that unknown keys generate warning logs."""
        key_map = {
            "SimpleKey": "value",
            # "CamelCaseKey" is missing, should generate warning
        }
        
        # This test mainly checks that the function doesn't crash with unknown keys
        # In a real test environment, you might want to capture and verify log output
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.simple_key, "simple_value")
        # Unknown key should be ignored, not cause an error

    def test_error_cases(self):
        """Test various error conditions."""
        
        # Test invalid key_to_parser_function_map type
        with self.assertRaises(TypeError):
            process_key_to_parser_function("invalid", {}, self.mock_obj)
        
        # Test set_attrs=True without obj
        with self.assertRaises(ValueError):
            process_key_to_parser_function({}, {}, obj=None, set_attrs=True)
        
        # Test DICT_ENTRY without target_dict_path
        with self.assertRaises(ValueError):
            key_map = {
                "SimpleKey": {
                    'action': ParseAction.DICT_ENTRY,
                    'target': 'test'
                    # missing target_dict_path
                }
            }
            process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        # Test invalid parser type
        with self.assertRaises(TypeError):
            key_map = {
                "SimpleKey": {
                    'parser': 123  # Invalid parser type
                }
            }
            process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        # Test invalid target type
        with self.assertRaises(ValueError):
            key_map = {
                "SimpleKey": {
                    'target': 123  # Invalid target type
                }
            }
            process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        # Test invalid config type
        with self.assertRaises(TypeError):
            key_map = {
                "SimpleKey": 123  # Invalid config type
            }
            process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)

    def test_invalid_default_configuration(self):
        """Test invalid default configuration keys."""
        with self.assertRaises(ValueError):
            invalid_config = {
                'invalid_key': 'invalid_value'
            }
            process_key_to_parser_function({}, {}, self.mock_obj, default_configuration=invalid_config)

    def test_complex_nested_structure(self):
        """Test complex nested dictionary structures."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'level1.level2.level3',
                'target': 'deep_key'
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.level1["level2"]["level3"]["deep_key"], "simple_value")

    def test_complex_nested_structure_works_without_set_attrs(self):
        """Test that complex nested structures work correctly with set_attrs=False."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'level1.level2.level3',
                'target': 'deep_key'
            }
        }
        
        result = process_key_to_parser_function(
            key_map, self.sample_data, obj=None, set_attrs=False
        )
        
        self.assertEqual(result["level1"]["level2"]["level3"]["deep_key"], "simple_value")

    def test_log_descriptor(self):
        """Test log_descriptor option."""
        key_map = {
            "UnknownKey": "value",  # This will generate a warning
        }
        
        # Test that log_descriptor is used (function should not crash)
        process_key_to_parser_function(
            key_map, {"UnknownKey": "test"}, self.mock_obj, 
            log_descriptor="test_context"
        )

    def test_tabs_option(self):
        """Test tabs option for logging."""
        key_map = {
            "UnknownKey": "value",  # This will generate a warning
        }
        
        # Test that tabs option is accepted (function should not crash)
        process_key_to_parser_function(
            key_map, {"UnknownKey": "test"}, self.mock_obj, 
            tabs=2
        )

    def test_mixed_configuration_formats(self):
        """Test mixing different configuration formats."""
        def custom_parser(value):
            return f"parsed_{value}"
        
        key_map = {
            "SimpleKey": "value",  # Simple string
            "CamelCaseKey": custom_parser,  # Function
            "NumberValue": (lambda x: x * 3, "tripled"),  # Tuple format
            "BooleanValue": {  # Dict format
                'parser': lambda x: not x,
                'target': 'inverted_boolean'
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.simple_key, "simple_value")
        self.assertEqual(self.mock_obj.camel_case_key, "parsed_camel_value")
        self.assertEqual(self.mock_obj.tripled, 126)  # 42 * 3
        self.assertEqual(self.mock_obj.inverted_boolean, False)  # not True

    def test_existing_nested_attributes(self):
        """Test behavior when nested attributes already exist."""
        # Pre-create some nested structure
        self.mock_obj.existing_dict = {"existing_key": "existing_value"}
        
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'existing_dict',
                'target': 'new_key'
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        # Should preserve existing data and add new
        self.assertEqual(self.mock_obj.existing_dict["existing_key"], "existing_value")
        self.assertEqual(self.mock_obj.existing_dict["new_key"], "simple_value")

    def test_target_dict_path_with_attribute_action_ignored(self):
        """Test that target_dict_path is ignored for ATTRIBUTE action."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.ATTRIBUTE,
                'target_dict_path': 'should_be_ignored',  # This should be ignored
                'target': 'simple_attr'
            }
        }
        
        # Should not raise an error (previously did, now allowed but ignored)
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.simple_attr, "simple_value")
        self.assertFalse(hasattr(self.mock_obj, "should_be_ignored"))

    def test_empty_data(self):
        """Test processing empty data."""
        key_map = {
            "SimpleKey": "value",
        }
        
        result = process_key_to_parser_function(key_map, {}, obj=None, set_attrs=False)
        
        self.assertEqual(result, {})

    def test_empty_key_map(self):
        """Test processing with empty key map."""
        result = process_key_to_parser_function({}, self.sample_data, obj=None, set_attrs=False)
        
        self.assertEqual(result, {})

    def test_mixed_object_dict_navigation(self):
        """Test navigation through mixed object attributes and dictionaries."""
        # Pre-populate object with a dictionary attribute
        self.mock_obj.config = {"nested": {"deep": "existing_value"}}
        
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'config.nested.deeper',
                'target': 'new_key'
            },
            "NumberValue": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'config.nested',
                'target': 'existing_level'
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        # Should preserve existing nested data
        self.assertEqual(self.mock_obj.config["nested"]["deep"], "existing_value")
        # Should add new nested data
        self.assertEqual(self.mock_obj.config["nested"]["deeper"]["new_key"], "simple_value")
        self.assertEqual(self.mock_obj.config["nested"]["existing_level"], 42)

    def test_single_level_dict_entry(self):
        """Test DICT_ENTRY with single level (no dots in path)."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'single_level',
                'target': 'test_key'
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.single_level["test_key"], "simple_value")

    def test_deeply_nested_path_creation(self):
        """Test creating very deep nested paths."""
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'a.b.c.d.e.f',
                'target': 'final_key'
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.a["b"]["c"]["d"]["e"]["f"]["final_key"], "simple_value")

    def test_overwrite_existing_dict_values(self):
        """Test overwriting existing dictionary values."""
        # Pre-populate with existing data
        self.mock_obj.data = {"key1": "old_value", "key2": "keep_this"}
        
        key_map = {
            "SimpleKey": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'data',
                'target': 'key1'  # This should overwrite
            },
            "NumberValue": {
                'action': ParseAction.DICT_ENTRY,
                'target_dict_path': 'data',
                'target': 'key3'  # This should add new
            }
        }
        
        process_key_to_parser_function(key_map, self.sample_data, self.mock_obj)
        
        self.assertEqual(self.mock_obj.data["key1"], "simple_value")  # Overwritten
        self.assertEqual(self.mock_obj.data["key2"], "keep_this")     # Preserved
        self.assertEqual(self.mock_obj.data["key3"], 42)             # New


if __name__ == '__main__':
    unittest.main()