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
    """Test cases for parse_hex, which returns both the RGBA channels and the Hex string."""

    def test_direct_structure(self):
        data = {"R": 255, "G": 0, "B": 0, "A": 255, "Hex": "FF0000FF"}
        result = parse_hex(data)
        self.assertEqual(result, {
            "RGBA": {"R": 255, "G": 0, "B": 0, "A": 255},
            "Hex": "FF0000FF"
        })

    def test_specified_color_structure(self):
        data = {"SpecifiedColor": {"R": 0, "G": 255, "B": 0, "A": 128, "Hex": "00FF0080"}}
        result = parse_hex(data)
        self.assertEqual(result, {
            "RGBA": {"R": 0, "G": 255, "B": 0, "A": 128},
            "Hex": "00FF0080"
        })

    def test_prefers_specified_color(self):
        data = {
            "R": 1, "G": 1, "B": 1, "A": 1, "Hex": "01010101",
            "SpecifiedColor": {"R": 2, "G": 2, "B": 2, "A": 2, "Hex": "02020202"}
        }
        result = parse_hex(data)
        self.assertEqual(result["Hex"], "02020202")
        self.assertEqual(result["RGBA"], {"R": 2, "G": 2, "B": 2, "A": 2})

    def test_rgba_and_hex_kept_even_when_they_disagree(self):
        """Game data sometimes has RGBA and Hex that don't match, so both are kept as-is."""
        data = {"R": 10, "G": 20, "B": 30, "A": 40, "Hex": "FFFFFFFF"}
        result = parse_hex(data)
        self.assertEqual(result["RGBA"], {"R": 10, "G": 20, "B": 30, "A": 40})
        self.assertEqual(result["Hex"], "FFFFFFFF")

    def test_additional_keys_ignored(self):
        data = {"R": 1, "G": 2, "B": 3, "A": 4, "Hex": "01020304", "Name": "Custom", "LinearColor": {}}
        result = parse_hex(data)
        self.assertEqual(set(result.keys()), {"RGBA", "Hex"})
        self.assertEqual(set(result["RGBA"].keys()), {"R", "G", "B", "A"})

    def test_missing_key_raises_error(self):
        for missing in ["R", "G", "B", "A", "Hex"]:
            data = {"R": 1, "G": 2, "B": 3, "A": 4, "Hex": "01020304"}
            del data[missing]
            with self.subTest(missing=missing):
                with self.assertRaises(KeyError):
                    parse_hex(data)

    def test_empty_structures_raise_error(self):
        with self.assertRaises(KeyError):
            parse_hex({})
        with self.assertRaises(KeyError):
            parse_hex({"SpecifiedColor": {}})


if __name__ == '__main__':
    unittest.main()
