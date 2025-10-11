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

parse_hex = src_utils.parse_hex


class TestParseHex(unittest.TestCase):
    """Test cases for the parse_hex function."""
    
    def test_direct_hex_structure(self):
        """Test extracting hex from direct structure with Hex key."""
        data = {"Hex": "#FF0000"}
        result = parse_hex(data)
        self.assertEqual(result, "#FF0000")
        
        data = {"Hex": "0xFF00FF"}
        result = parse_hex(data)
        self.assertEqual(result, "0xFF00FF")
        
        data = {"Hex": "AABBCC"}
        result = parse_hex(data)
        self.assertEqual(result, "AABBCC")
    
    def test_specified_color_structure(self):
        """Test extracting hex from SpecifiedColor nested structure."""
        data = {
            "SpecifiedColor": {
                "Hex": "#00FF00"
            }
        }
        result = parse_hex(data)
        self.assertEqual(result, "#00FF00")
        
        # With additional keys in SpecifiedColor
        data = {
            "SpecifiedColor": {
                "Hex": "#123456",
                "Alpha": 255,
                "Other": "value"
            }
        }
        result = parse_hex(data)
        self.assertEqual(result, "#123456")
    
    def test_complex_nested_structure(self):
        """Test with complex nested structures containing SpecifiedColor."""
        data = {
            "ColorData": "unused",
            "SpecifiedColor": {
                "Hex": "#ABCDEF",
                "RGB": {
                    "R": 171,
                    "G": 205,
                    "B": 239
                }
            },
            "Other": "data"
        }
        result = parse_hex(data)
        self.assertEqual(result, "#ABCDEF")
    
    def test_different_hex_formats(self):
        """Test with different hex color formats."""
        # Standard 6-digit hex with #
        data = {"Hex": "#FF0000"}
        self.assertEqual(parse_hex(data), "#FF0000")
        
        # Standard 6-digit hex without #
        data = {"Hex": "FF0000"}
        self.assertEqual(parse_hex(data), "FF0000")
        
        # 8-digit hex with alpha
        data = {"Hex": "#FF0000FF"}
        self.assertEqual(parse_hex(data), "#FF0000FF")
        
        # Lowercase hex
        data = {"Hex": "#ff0000"}
        self.assertEqual(parse_hex(data), "#ff0000")
        
        # Mixed case
        data = {"Hex": "#FfAaBb"}
        self.assertEqual(parse_hex(data), "#FfAaBb")
    
    def test_numeric_hex_values(self):
        """Test with numeric hex representations."""
        data = {"Hex": 0xFF0000}
        result = parse_hex(data)
        self.assertEqual(result, 0xFF0000)
        
        data = {"Hex": 16777215}  # 0xFFFFFF in decimal
        result = parse_hex(data)
        self.assertEqual(result, 16777215)
    
    def test_prefers_specified_color(self):
        """Test that SpecifiedColor takes precedence over direct Hex."""
        data = {
            "Hex": "#FF0000",  # This should be ignored
            "SpecifiedColor": {
                "Hex": "#00FF00"  # This should be returned
            }
        }
        result = parse_hex(data)
        self.assertEqual(result, "#00FF00")
    
    def test_missing_hex_key_raises_error(self):
        """Test that missing Hex key raises KeyError."""
        # Direct structure without Hex
        data = {"Color": "#FF0000"}
        with self.assertRaises(KeyError):
            parse_hex(data)
        
        # SpecifiedColor structure without Hex
        data = {
            "SpecifiedColor": {
                "RGB": {"R": 255, "G": 0, "B": 0}
            }
        }
        with self.assertRaises(KeyError):
            parse_hex(data)
    
    def test_empty_structures(self):
        """Test behavior with empty structures."""
        # Empty dict
        data = {}
        with self.assertRaises(KeyError):
            parse_hex(data)
        
        # SpecifiedColor with empty dict
        data = {"SpecifiedColor": {}}
        with self.assertRaises(KeyError):
            parse_hex(data)
    
    def test_none_values(self):
        """Test behavior with None values."""
        # None in Hex key
        data = {"Hex": None}
        result = parse_hex(data)
        self.assertIsNone(result)
        
        # None in SpecifiedColor Hex
        data = {"SpecifiedColor": {"Hex": None}}
        result = parse_hex(data)
        self.assertIsNone(result)
    
    def test_empty_string_hex(self):
        """Test behavior with empty string hex values."""
        data = {"Hex": ""}
        result = parse_hex(data)
        self.assertEqual(result, "")
        
        data = {"SpecifiedColor": {"Hex": ""}}
        result = parse_hex(data)
        self.assertEqual(result, "")
    
    def test_game_specific_examples(self):
        """Test with game-specific color data structures."""
        # Typical game color structure
        game_color_data = {
            "ColorType": "Custom",
            "SpecifiedColor": {
                "Hex": "#FF4500",
                "LinearColor": {
                    "R": 1.0,
                    "G": 0.271,
                    "B": 0.0,
                    "A": 1.0
                }
            }
        }
        result = parse_hex(game_color_data)
        self.assertEqual(result, "#FF4500")
        
        # Simple direct hex
        simple_color = {"Hex": "#800080"}
        result = parse_hex(simple_color)
        self.assertEqual(result, "#800080")
    
    def test_additional_keys_ignored(self):
        """Test that additional keys in the data structure are ignored."""
        data = {
            "Hex": "#123456",
            "Name": "Custom Color",
            "Type": "Specified",
            "Alpha": 1.0,
            "SpecifiedColor": {
                "Hex": "#654321",
                "ExtraData": "ignored"
            }
        }
        # Should prefer SpecifiedColor
        result = parse_hex(data)
        self.assertEqual(result, "#654321")


if __name__ == '__main__':
    unittest.main()
