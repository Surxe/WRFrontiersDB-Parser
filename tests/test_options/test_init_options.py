import unittest
import sys
import os
import tempfile
import shutil
import argparse
from unittest.mock import patch, Mock

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.options module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_options", os.path.join(src_path, "options.py"))
src_options = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_options)

Options = src_options.Options
init_options = src_options.init_options

def create_args(**kwargs):
    """Helper function to create argparse Namespace with given arguments."""
    # Convert kwargs to use underscores instead of hyphens for argparse compatibility
    converted_kwargs = {}
    for key, value in kwargs.items():
        # Convert hyphens to underscores for argparse attribute names
        attr_name = key.replace('-', '_')
        converted_kwargs[attr_name] = value
    
    return argparse.Namespace(**converted_kwargs)


class TestInitOptions(unittest.TestCase):
    """Test cases for the init_options function.
    
    The init_options function is a factory function that creates a Options object
    with provided arguments, falling back to environment variables.
    """

    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_dir = os.path.join(self.temp_dir, "export")
        self.output_dir = os.path.join(self.temp_dir, "output")
        
        # Create required directories
        os.makedirs(self.export_dir)
        os.makedirs(self.output_dir)

    def tearDown(self):
        """Clean up temporary directories."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch.dict(os.environ, {}, clear=True)
    def test_init_options_with_all_arguments(self):
        """Test init_options creates Options with all provided arguments."""
        
        args = create_args(
            log_level="INFO",
            should_parse=True,
            game_name="WRFrontiers",
            export_dir=self.export_dir,
            output_dir=self.output_dir,
            should_push_data=True,
            game_version="2025-10-11",
            target_branch="main",
            gh_data_repo_pat="test_token_123"
        )
        options = init_options(args)
        
        # Verify all options are set correctly
        self.assertEqual(options.log_level, "INFO")
        self.assertTrue(options.should_parse)
        self.assertEqual(options.game_name, "WRFrontiers")
        self.assertEqual(options.export_dir, self.export_dir)
        self.assertEqual(options.output_dir, self.output_dir)
        self.assertTrue(options.should_push_data)
        self.assertEqual(options.game_version, "2025-10-11")
        self.assertEqual(options.target_branch, "main")
        self.assertEqual(options.gh_data_repo_pat, "test_token_123")

    @patch.dict(os.environ, {
        'LOG_LEVEL': 'ERROR',
        'SHOULD_PARSE': 'True',
        'GAME_NAME': 'WRFrontiers',
        'EXPORT_DIR': '/tmp/test/export',
        'OUTPUT_DIR': '/tmp/test/output',
        'SHOULD_PUSH_DATA': 'True',
        'GAME_VERSION': '2025-10-11',
        'TARGET_BRANCH': 'testing-grounds',
        'GH_DATA_REPO_PAT': 'test_pat_token',
    })
    def test_init_options_with_environment_fallback(self):
        """Test init_options falls back to environment variables."""
        options = init_options()
        
        # Verify environment variables are used
        self.assertEqual(options.log_level, "ERROR")
        self.assertTrue(options.should_parse)
        self.assertEqual(options.game_name, "WRFrontiers")
        self.assertEqual(options.export_dir, "/tmp/test/export")
        self.assertEqual(options.output_dir, "/tmp/test/output")
        self.assertTrue(options.should_push_data)
        self.assertEqual(options.game_version, "2025-10-11")
        self.assertEqual(options.target_branch, "testing-grounds")
        self.assertEqual(options.gh_data_repo_pat, "test_pat_token")

    @patch.dict(os.environ, {
        'LOG_LEVEL': 'WARNING',
        'SHOULD_PARSE': 'True',
        'GAME_NAME': 'envuser',
        'EXPORT_DIR': '/env/export',
        'OUTPUT_DIR': '/env/output'
    })
    def test_init_options_argument_override_environment(self):
        """Test init_options arguments override environment variables."""
        args = create_args(
            log_level="CRITICAL",
            should_parse=True,
            game_name="arguser",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        options = init_options(args)
        
        # Arguments should override environment
        self.assertEqual(options.log_level, "CRITICAL")  # Overridden
        self.assertEqual(options.game_name, "arguser")  # Overridden
        self.assertEqual(options.export_dir, self.export_dir)  # Overridden
        self.assertEqual(options.output_dir, self.output_dir)  # Overridden

    def test_init_options_returns_options_object(self):
        """Test init_options returns a Options instance."""
        args = create_args(
            log_level="DEBUG",
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        options = init_options(args)
        
        self.assertIsInstance(options, Options)

    def test_init_options_sets_global_options(self):
        """Test init_options sets the global OPTIONS variable."""
        args = create_args(
            log_level="DEBUG",
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        options = init_options(args)
        
        # Check that global OPTIONS is set
        self.assertEqual(src_options.OPTIONS, options)

    @patch.dict(os.environ, {}, clear=True)  # Clear environment to test pure defaults
    def test_init_options_with_none_values(self):
        """Test init_options handles None values correctly."""
        # Provide some args as None to test fallback behavior
        args = create_args(
            log_level=None,  # Should use default
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        options = init_options(args)
        
        # None values should trigger fallback to environment/defaults
        self.assertEqual(options.log_level, "DEBUG")  # Default
        self.assertEqual(options.game_name, "test")

    @patch.dict(os.environ, {}, clear=True)  # Clear environment to test pure defaults
    def test_init_options_partial_arguments(self):
        """Test init_options with only some arguments provided."""
        args = create_args(
            log_level="INFO",
            should_parse=True,
            game_name="partialtest",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        options = init_options(args)
        
        # Provided arguments should be set
        self.assertEqual(options.log_level, "INFO")
        self.assertEqual(options.game_name, "partialtest")
        
        # Unprovided arguments should use defaults
        self.assertFalse(options.should_push_data)  # Default False

    @patch.dict(os.environ, {}, clear=True)
    def test_init_options_defaults_when_no_root_options_set(self):
        """Test that all root options default to True when none are explicitly set."""
        # Don't provide any root options (should_parse, should_push_data)
        # But provide all required sub-options since they'll be defaulted to True
        args = create_args(
            log_level="INFO",
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir,
            game_version="2025-10-11",  # Required for should_push_data
            gh_data_repo_pat="test_token"  # Required for should_push_data
        )
        options = init_options(args)
        
        # When no root options are set, they should all default to True
        self.assertTrue(options.should_parse)
        self.assertTrue(options.should_push_data)


if __name__ == '__main__':
    unittest.main()