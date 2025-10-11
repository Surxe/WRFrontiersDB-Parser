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

parse_editor_curve_data = src_utils.parse_editor_curve_data
expected_curve_data = src_utils.expected_curve_data


class TestParseEditorCurveData(unittest.TestCase):
    """Test cases for the parse_editor_curve_data function."""
    
    def setUp(self):
        """Set up common test data."""
        # Valid curve element with all expected fields
        self.valid_curve_element = {
            "Time": 1.0,
            "Value": 100.0,
            "InterpMode": "RCIM_Linear",
            "TangentMode": "RCTM_Auto",
            "TangentWeightMode": "RCTWM_WeightedNone",
            "ArriveTangent": 0.0,
            "ArriveTangentWeight": 0.0,
            "LeaveTangent": 0.0,
            "LeaveTangentWeight": 0.0
        }
        
        # Expected parsed output
        self.expected_parsed_element = {
            "Time": 1.0,
            "Value": 100.0,
            "InterpMode": "RCIM_Linear"
        }
    
    def test_empty_data_returns_none(self):
        """Test that empty data returns None."""
        data = {}
        result = parse_editor_curve_data(data)
        self.assertIsNone(result)
    
    def test_no_keys_returns_data_as_is(self):
        """Test that data without 'Keys' is returned as-is."""
        data = {
            "SomeProperty": "value",
            "AnotherProperty": 42
        }
        result = parse_editor_curve_data(data)
        self.assertEqual(result, data)
    
    def test_dist_to_damage_structure_with_keys(self):
        """Test parsing DistToDamage structure with Keys."""
        data = {
            "DistToDamage": {
                "Keys": [self.valid_curve_element]
            },
            "OtherProperty": "preserved"
        }
        
        result = parse_editor_curve_data(data)
        
        expected = {
            "DistToDamage": [self.expected_parsed_element],
            "OtherProperty": "preserved"
        }
        self.assertEqual(result, expected)
    
    def test_float_curve_structure_with_keys(self):
        """Test parsing FloatCurve structure with Keys."""
        data = {
            "FloatCurve": {
                "Keys": [self.valid_curve_element]
            }
        }
        
        result = parse_editor_curve_data(data)
        expected = [self.expected_parsed_element]
        self.assertEqual(result, expected)
    
    def test_direct_keys_structure(self):
        """Test parsing data that directly contains Keys."""
        data = {
            "Keys": [self.valid_curve_element]
        }
        
        result = parse_editor_curve_data(data)
        expected = [self.expected_parsed_element]
        self.assertEqual(result, expected)
    
    def test_nested_editor_curve_data(self):
        """Test parsing with nested EditorCurveData structure."""
        data = {
            "DistToDamage": {
                "EditorCurveData": {
                    "Keys": [self.valid_curve_element]
                }
            }
        }
        
        result = parse_editor_curve_data(data)
        expected = {
            "DistToDamage": [self.expected_parsed_element]
        }
        self.assertEqual(result, expected)
    
    def test_key_handles_to_indices_removed(self):
        """Test that KeyHandlesToIndices is removed from data."""
        data = {
            "Keys": [self.valid_curve_element],
            "KeyHandlesToIndices": {"handle1": 0, "handle2": 1}
        }
        
        result = parse_editor_curve_data(data)
        expected = [self.expected_parsed_element]
        self.assertEqual(result, expected)
    
    def test_multiple_curve_elements(self):
        """Test parsing multiple curve elements."""
        element2 = self.valid_curve_element.copy()
        element2["Time"] = 2.0
        element2["Value"] = 200.0
        element2["InterpMode"] = "RCIM_Constant"
        
        data = {
            "Keys": [self.valid_curve_element, element2]
        }
        
        result = parse_editor_curve_data(data)
        
        expected_element2 = {
            "Time": 2.0,
            "Value": 200.0,
            "InterpMode": "RCIM_Constant"
        }
        expected = [self.expected_parsed_element, expected_element2]
        self.assertEqual(result, expected)
    
    def test_missing_required_key_raises_error(self):
        """Test that missing required keys raise ValueError."""
        invalid_element = self.valid_curve_element.copy()
        del invalid_element["TangentMode"]  # Remove required key
        
        data = {
            "Keys": [invalid_element]
        }
        
        with self.assertRaises(ValueError) as context:
            parse_editor_curve_data(data)
        
        self.assertIn("Missing expected key 'TangentMode'", str(context.exception))
    
    def test_unexpected_value_raises_error(self):
        """Test that unexpected values for required keys raise ValueError."""
        invalid_element = self.valid_curve_element.copy()
        invalid_element["TangentMode"] = "WRONG_VALUE"  # Invalid value
        
        data = {
            "Keys": [invalid_element]
        }
        
        with self.assertRaises(ValueError) as context:
            parse_editor_curve_data(data)
        
        self.assertIn("Unexpected value for key 'TangentMode'", str(context.exception))
        self.assertIn("WRONG_VALUE (expected: RCTM_Auto)", str(context.exception))
    
    def test_all_expected_curve_data_fields(self):
        """Test validation of all expected curve data fields."""
        # Test each field individually
        for field_name, expected_value in expected_curve_data.items():
            with self.subTest(field=field_name):
                invalid_element = self.valid_curve_element.copy()
                invalid_element[field_name] = "INVALID_VALUE"
                
                data = {"Keys": [invalid_element]}
                
                with self.assertRaises(ValueError) as context:
                    parse_editor_curve_data(data)
                
                self.assertIn(f"Unexpected value for key '{field_name}'", str(context.exception))
    
    def test_missing_time_field(self):
        """Test that missing Time field causes KeyError (not handled by function)."""
        invalid_element = self.valid_curve_element.copy()
        del invalid_element["Time"]
        
        data = {"Keys": [invalid_element]}
        
        with self.assertRaises(KeyError):
            parse_editor_curve_data(data)
    
    def test_missing_value_field(self):
        """Test that missing Value field causes KeyError (not handled by function)."""
        invalid_element = self.valid_curve_element.copy()
        del invalid_element["Value"]
        
        data = {"Keys": [invalid_element]}
        
        with self.assertRaises(KeyError):
            parse_editor_curve_data(data)
    
    def test_missing_interp_mode_field(self):
        """Test that missing InterpMode field causes KeyError (not handled by function)."""
        invalid_element = self.valid_curve_element.copy()
        del invalid_element["InterpMode"]
        
        data = {"Keys": [invalid_element]}
        
        with self.assertRaises(KeyError):
            parse_editor_curve_data(data)
    
    def test_game_curve_data_example(self):
        """Test with realistic game curve data."""
        game_data = {
            "DistToDamage": {
                "EditorCurveData": {
                    "Keys": [
                        {
                            "Time": 0.0,
                            "Value": 100.0,
                            "InterpMode": "RCIM_Linear",
                            "TangentMode": "RCTM_Auto",
                            "TangentWeightMode": "RCTWM_WeightedNone",
                            "ArriveTangent": 0.0,
                            "ArriveTangentWeight": 0.0,
                            "LeaveTangent": 0.0,
                            "LeaveTangentWeight": 0.0
                        },
                        {
                            "Time": 10.0,
                            "Value": 80.0,
                            "InterpMode": "RCIM_Cubic",
                            "TangentMode": "RCTM_Auto",
                            "TangentWeightMode": "RCTWM_WeightedNone",
                            "ArriveTangent": 0.0,
                            "ArriveTangentWeight": 0.0,
                            "LeaveTangent": 0.0,
                            "LeaveTangentWeight": 0.0
                        }
                    ],
                    "KeyHandlesToIndices": {"key1": 0, "key2": 1}
                }
            },
            "MaxRange": 50.0
        }
        
        result = parse_editor_curve_data(game_data)
        
        expected = {
            "DistToDamage": [
                {"Time": 0.0, "Value": 100.0, "InterpMode": "RCIM_Linear"},
                {"Time": 10.0, "Value": 80.0, "InterpMode": "RCIM_Cubic"}
            ],
            "MaxRange": 50.0
        }
        self.assertEqual(result, expected)
    
    def test_nested_structure_not_processed(self):
        """Test that nested DistToDamage structures are not processed (only top-level)."""
        data = {
            "WeaponStats": {
                "DamageProfile": {
                    "DistToDamage": {
                        "Keys": [self.valid_curve_element]
                    }
                },
                "Accuracy": 95.0,
                "Range": 100.0
            },
            "WeaponType": "Rifle"
        }
        
        result = parse_editor_curve_data(data)
        
        # Since DistToDamage is not at top level, data should be returned as-is
        self.assertEqual(result, data)
    
    def test_float_curve_priority_over_direct_keys(self):
        """Test that FloatCurve takes priority when both FloatCurve and direct keys exist."""
        data = {
            "FloatCurve": {
                "Keys": [self.valid_curve_element]
            },
            "Keys": [{"different": "data"}]  # This should be ignored
        }
        
        result = parse_editor_curve_data(data)
        expected = [self.expected_parsed_element]
        self.assertEqual(result, expected)
    
    def test_dist_to_damage_priority_over_float_curve(self):
        """Test that DistToDamage takes priority over FloatCurve."""
        element2 = self.valid_curve_element.copy()
        element2["Time"] = 5.0
        element2["Value"] = 50.0
        
        data = {
            "DistToDamage": {
                "Keys": [self.valid_curve_element]
            },
            "FloatCurve": {
                "Keys": [element2]  # This should be ignored
            }
        }
        
        result = parse_editor_curve_data(data)
        expected = {
            "DistToDamage": [self.expected_parsed_element],
            "FloatCurve": {
                "Keys": [element2]  # This remains unchanged since DistToDamage was processed
            }
        }
        self.assertEqual(result, expected)
    
    def test_empty_keys_array(self):
        """Test handling of empty Keys array."""
        data = {
            "Keys": []
        }
        
        result = parse_editor_curve_data(data)
        expected = []
        self.assertEqual(result, expected)
    
    def test_numeric_values_preserved(self):
        """Test that numeric values are properly preserved."""
        element_with_numbers = self.valid_curve_element.copy()
        element_with_numbers.update({
            "Time": 12.5,
            "Value": -75.25,
            "InterpMode": "RCIM_CubicClamped"
        })
        
        data = {"Keys": [element_with_numbers]}
        
        result = parse_editor_curve_data(data)
        
        expected = [{
            "Time": 12.5,
            "Value": -75.25,
            "InterpMode": "RCIM_CubicClamped"
        }]
        self.assertEqual(result, expected)
    
    def test_modifies_original_data_in_place_for_dist_to_damage(self):
        """Test that the function modifies original data in-place for DistToDamage."""
        original_data = {
            "DistToDamage": {
                "Keys": [self.valid_curve_element.copy()],
                "KeyHandlesToIndices": {"test": "value"}
            },
            "PreserveThis": "value"
        }
        
        result = parse_editor_curve_data(original_data)
        
        # The function should modify the original data in-place for DistToDamage
        expected = {
            "DistToDamage": [self.expected_parsed_element],
            "PreserveThis": "value"
        }
        
        # Both result and original_data should be the same (modified in-place)
        self.assertEqual(result, expected)
        self.assertEqual(original_data, expected)
        self.assertIs(result, original_data)  # Same object reference
    
    def test_float_curve_does_not_modify_original_data(self):
        """Test that FloatCurve processing doesn't modify original data."""
        original_data = {
            "FloatCurve": {
                "Keys": [self.valid_curve_element.copy()]
            },
            "PreserveThis": "value"
        }
        
        import copy
        data_before_call = copy.deepcopy(original_data)
        
        result = parse_editor_curve_data(original_data)
        
        # Original data should be unchanged for FloatCurve
        self.assertEqual(original_data, data_before_call)
        
        # Result should just be the parsed curve data
        expected = [self.expected_parsed_element]
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()