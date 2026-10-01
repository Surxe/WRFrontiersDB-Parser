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
parse_curve = src_utils.parse_curve
parse_editor_curve_data = src_utils.parse_editor_curve_data


class TestParseEditorCurveData(unittest.TestCase):
    """EditorCurveData is kept 1:1 with the game data; parse_curve only routes to it."""

    def setUp(self):
        self.curve_data = {
            "Keys": [
                {"Time": 0.0, "Value": 100.0, "InterpMode": "RCIM_Linear"},
                {"Time": 1.0, "Value": 50.0, "InterpMode": "RCIM_Linear"}
            ],
            "DefaultValue": 3.4028234663852886e+38,
            "PreInfinityExtrap": "RCCE_Constant",
            "PostInfinityExtrap": "RCCE_Constant"
        }

    def test_parse_editor_curve_data_is_identity(self):
        result = parse_editor_curve_data(self.curve_data)
        self.assertIs(result, self.curve_data)

    def test_dist_to_damage_curve_preserved(self):
        data = {"DistToDamage": {"EditorCurveData": self.curve_data, "ExternalCurve": None}}
        result = parse_curve(data)
        self.assertEqual(result["DistToDamage"]["EditorCurveData"], self.curve_data)
        self.assertIsNone(result["DistToDamage"]["ExternalCurve"])

    def test_float_curve_preserved(self):
        data = {"FloatCurve": {"EditorCurveData": self.curve_data}}
        result = parse_curve(data)
        self.assertEqual(result["FloatCurve"]["EditorCurveData"], self.curve_data)

    def test_data_without_curve_returned_as_is(self):
        data = {"Keys": [{"Time": 0.0, "Value": 1.0}], "Other": "value"}
        self.assertEqual(parse_curve(data), {"Keys": [{"Time": 0.0, "Value": 1.0}], "Other": "value"})

    def test_empty_data_returned_as_is(self):
        self.assertEqual(parse_curve({}), {})

    def test_curve_key_without_editor_curve_data_untouched(self):
        data = {"FloatCurve": {"ExternalCurve": "/Game/Curves/C_Thing.C_Thing"}}
        self.assertEqual(parse_curve(data), {"FloatCurve": {"ExternalCurve": "/Game/Curves/C_Thing.C_Thing"}})


if __name__ == '__main__':
    unittest.main()
