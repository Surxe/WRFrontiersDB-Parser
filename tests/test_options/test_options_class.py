import unittest
import sys
import os
import tempfile
import shutil
import argparse
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# Add the src directory to the Python path to import options
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.options module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_options", os.path.join(src_path, "options.py"))
src_options = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_options)

Options = src_options.Options

def create_args(**kwargs):
    """Helper function to create argparse Namespace with given arguments."""
    # Convert kwargs to use underscores instead of hyphens for argparse compatibility
    converted_kwargs = {}
    for key, value in kwargs.items():
        # Convert hyphens to underscores for argparse attribute names
        attr_name = key.replace('-', '_')
        converted_kwargs[attr_name] = value
    
    return argparse.Namespace(**converted_kwargs)


class TestOptions(unittest.TestCase):
    """Test cases for the Options class.
    
    The Options class handles configuration options with environment variable fallback,
    validation, and logging setup.
    """

    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_dir = os.path.join(self.temp_dir, "export")
        self.output_dir = os.path.join(self.temp_dir, "output")
        self.mapper_dir = os.path.join(self.temp_dir, "mapper")
        
        # Create required directories
        os.makedirs(self.export_dir)
        os.makedirs(self.output_dir)
        os.makedirs(self.mapper_dir)

    def tearDown(self):
        """Clean up temporary directories."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch.object(src_options, 'logger')
    def test_options_init_with_no_args(self, mock_logger):
        """Test Options initialization with no arguments (should raise validation error)."""
        # Mock logger.add and logger.remove to avoid actual logging setup
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # When no args are provided, root options default to True but required dependent options are missing
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                Options()
            
        # Should raise validation error for missing required options
        # The error will be about the first missing required option encountered
        error_message = str(context.exception)
        self.assertIn("is required when any of the following are true", error_message)
        # At least one of the required options should be mentioned
        self.assertTrue(
            "EXPORT_DIR" in error_message or "OUTPUT_DIR" in error_message or "GAME_VERSION" in error_message,
            f"Expected one of the required options in error message: {error_message}"
        )

    @patch.object(src_options, 'logger')
    def test_options_init_with_args(self, mock_logger):
        """Test Options initialization with argparse arguments."""
        # Mock logger methods
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        args = create_args(
            log_level="INFO",
            should_parse=True,
            game_name="WRFrontiers",
            export_dir=self.export_dir,
            output_dir=self.output_dir,
            should_push_data=True,
            game_version="2025-10-11",
            target_branch="main",
            gh_data_repo_pat="test_token"
        )
        
        with patch.dict(os.environ, {}, clear=True):
            options = Options(args)
        
        # Verify all options are set correctly
        self.assertEqual(options.log_level, "INFO")
        self.assertTrue(options.should_parse)
        self.assertEqual(options.game_name, "WRFrontiers")
        self.assertEqual(options.export_dir, self.export_dir)
        self.assertEqual(options.output_dir, self.output_dir)
        self.assertTrue(options.should_push_data)
        self.assertEqual(options.game_version, "2025-10-11")
        self.assertEqual(options.target_branch, "main")
        self.assertEqual(options.gh_data_repo_pat, "test_token")

    @patch.object(src_options, 'logger')
    def test_options_environment_variable_fallback(self, mock_logger):
        """Test Options falls back to environment variables when args not provided."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        env_vars = {
            'LOG_LEVEL': 'ERROR',
            'SHOULD_PARSE': 'True',
            'GAME_NAME': 'WRFrontiers',
            'EXPORT_DIR': '/tmp/env/export',
            'OUTPUT_DIR': '/tmp/env/output',
            'SHOULD_PUSH_DATA': 'True',
            'GAME_VERSION': '2025-10-11',
            'TARGET_BRANCH': 'testing-grounds',
            'GH_DATA_REPO_PAT': 'env_token'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = Options()
        
        # Verify environment variables are used
        self.assertEqual(options.log_level, "ERROR")
        self.assertTrue(options.should_parse)
        self.assertEqual(options.game_name, "WRFrontiers")
        self.assertEqual(options.export_dir, "/tmp/env/export")
        self.assertEqual(options.output_dir, "/tmp/env/output")
        self.assertTrue(options.should_push_data)
        self.assertEqual(options.game_version, "2025-10-11")
        self.assertEqual(options.target_branch, "testing-grounds")
        self.assertEqual(options.gh_data_repo_pat, "env_token")

    @patch.object(src_options, 'logger')
    def test_options_args_override_environment(self, mock_logger):
        """Test that command line arguments override environment variables."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        env_vars = {
            'LOG_LEVEL': 'WARNING',
            'SHOULD_PARSE': 'True',
            'GAME_NAME': 'envuser',
            'EXPORT_DIR': '/env/export',
            'OUTPUT_DIR': '/env/output',
            'SHOULD_PUSH_DATA': 'True',
            'GAME_VERSION': '2025-01-01',
            'TARGET_BRANCH': 'env-branch',
            'GH_DATA_REPO_PAT': 'env-token'
        }
        
        args = create_args(
            log_level="CRITICAL",
            should_parse=True,
            game_name="arguser",
            export_dir=self.export_dir,
            output_dir=self.output_dir,
            should_push_data=True,
            game_version="2025-10-11",
            target_branch="arg-branch",
            gh_data_repo_pat="arg-token"
        )
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = Options(args)
        
        # Arguments should override environment
        self.assertEqual(options.log_level, "CRITICAL")  # Overridden
        self.assertEqual(options.game_name, "arguser")  # Overridden
        self.assertEqual(options.export_dir, self.export_dir)  # Overridden
        self.assertEqual(options.game_version, "2025-10-11")  # Overridden
        self.assertEqual(options.target_branch, "arg-branch")  # Overridden
        self.assertEqual(options.gh_data_repo_pat, "arg-token")  # Overridden

    @patch.object(src_options, 'logger')
    def test_options_type_conversion_from_env(self, mock_logger):
        """Test proper type conversion from environment variables."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        env_vars = {
            'LOG_LEVEL': 'DEBUG',
            'SHOULD_PARSE': 'true',  # String boolean
            'GAME_NAME': 'WRFrontiers',
            'EXPORT_DIR': self.export_dir,
            'OUTPUT_DIR': self.output_dir,
            'SHOULD_PUSH_DATA': 'false',  # String boolean
            'GAME_VERSION': '2025-10-11',
            'TARGET_BRANCH': 'main',
            'GH_DATA_REPO_PAT': 'test_token'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = Options()
        
        # Verify type conversions
        self.assertIsInstance(options.should_parse, bool)
        self.assertTrue(options.should_parse)  # 'true' -> True
        self.assertIsInstance(options.should_push_data, bool)
        self.assertFalse(options.should_push_data)  # 'false' -> False
        self.assertEqual(options.log_level, "DEBUG")
        self.assertEqual(options.game_name, "WRFrontiers")

    @patch.object(src_options, 'logger')
    def test_options_literal_type_validation(self, mock_logger):
        """Test Literal type validation for log level."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # Valid log level - provide all required options
        valid_env = {
            'LOG_LEVEL': 'INFO',
            'SHOULD_PARSE': 'True',
            'GAME_NAME': 'WRFrontiers',
            'EXPORT_DIR': self.export_dir,
            'OUTPUT_DIR': self.output_dir,
            'SHOULD_PUSH_DATA': 'True',
            'GAME_VERSION': '2025-10-11',
            'TARGET_BRANCH': 'main',
            'GH_DATA_REPO_PAT': 'test_token'
        }
        
        with patch.dict(os.environ, valid_env, clear=True):
            options = Options()
            self.assertEqual(options.log_level, "INFO")
        
        # Invalid log level should fall back to default
        invalid_env = valid_env.copy()
        invalid_env['LOG_LEVEL'] = 'INVALID_LEVEL'
        
        with patch.dict(os.environ, invalid_env, clear=True):
            options = Options()
            self.assertEqual(options.log_level, "DEBUG")  # Should fall back to default

    @patch.object(src_options, 'logger')
    def test_options_missing_required_dependent_options_raises_error(self, mock_logger):
        """Test that missing required dependent options raise ValueError."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # Enable should_parse but don't provide required dependent options
        args = create_args(
            should_parse=True,
            # Missing: export_dir, output_dir
            game_name="WRFrontiers"
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                Options(args)
            
            error_message = str(context.exception)
            self.assertIn("is required when any of the following are true", error_message)
            # Should mention SHOULD_PARSE as the active dependency
            self.assertIn("SHOULD_PARSE", error_message)
            # At least one of the required options should be mentioned
            self.assertTrue(
                "EXPORT_DIR" in error_message or "OUTPUT_DIR" in error_message,
                f"Expected EXPORT_DIR or OUTPUT_DIR in error message: {error_message}"
            )

    @patch.object(src_options, 'logger')
    def test_options_should_flags_explicit_false(self, mock_logger):
        """Test that should_* options can be explicitly set to False."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # Provide only non-should arguments and turn off all should flags
        args = create_args(
            log_level="INFO",
            should_parse=False,
            should_push_data=False
        )
        
        with patch.dict(os.environ, {}, clear=True):
            options = Options(args)
        
        # When explicitly set to False, they should remain False
        self.assertFalse(options.should_parse)
        self.assertFalse(options.should_push_data)

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_behavior_with_minimal_args(self, mock_print, mock_logger):
        """Test Options behavior with minimal arguments provided."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # Just test that we can create options with minimal args
        # and that the schema defaults are used appropriately
        args = create_args(
            log_level="INFO",
            should_parse=False,
            should_push_data=False
        )
        
        with patch.dict(os.environ, {}, clear=True):
            options = Options(args)
        
        # Verify the provided args are respected
        self.assertEqual(options.log_level, "INFO")
        self.assertFalse(options.should_parse)
        self.assertFalse(options.should_push_data)

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_attribute_name_conversion(self, mock_print, mock_logger):
        """Test that schema keys are converted to lowercase attribute names."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        args = create_args(
            log_level="DEBUG",
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        
        with patch.dict(os.environ, {}, clear=True):
            options = Options(args)
        
        # Test that schema keys (UPPER_CASE) become lowercase attributes
        self.assertTrue(hasattr(options, 'log_level'))  # LOG_LEVEL -> log_level
        self.assertTrue(hasattr(options, 'should_parse'))  # SHOULD_PARSE -> should_parse
        self.assertTrue(hasattr(options, 'game_name'))  # GAME_NAME -> game_name

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_validate_method_called(self, mock_print, mock_logger):
        """Test that validate method is called during initialization."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        args = create_args(
            log_level="DEBUG",
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Options, 'validate') as mock_validate:
                options = Options(args)
                mock_validate.assert_called_once()

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_log_method_called(self, mock_print, mock_logger):
        """Test that log method is called during initialization."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        args = create_args(
            log_level="DEBUG",
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Options, 'log') as mock_log:
                options = Options(args)
                mock_log.assert_called_once()

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_logger_setup(self, mock_print, mock_logger):
        """Test that logger is properly set up during initialization."""
        # Mock logger methods to capture calls
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        args = create_args(
            log_level="INFO",
            should_parse=True,
            game_name="test",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        
        with patch.dict(os.environ, {}, clear=True):
            options = Options(args)
        
        # Verify logger setup was called
        mock_logger.remove.assert_called()
        self.assertTrue(mock_logger.add.called)
        
        # Verify log level was set correctly
        self.assertEqual(options.log_level, "INFO")

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_sensitive_data_logging(self, mock_print, mock_logger):
        """Test that sensitive data is hidden in logs."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        mock_logger.info = Mock()
        
        args = create_args(
            log_level="DEBUG",
            should_parse=True,
            game_name="testuser",
            export_dir=self.export_dir,
            output_dir=self.output_dir
        )
        
        with patch.dict(os.environ, {}, clear=True):
            options = Options(args)
        
        # Check that logger.info was called with log lines
        mock_logger.info.assert_called()
        log_call_args = mock_logger.info.call_args[0][0]
        
        # Password should be hidden
        self.assertIn("***HIDDEN***", log_call_args)
        self.assertNotIn("secret_password", log_call_args)
        # Username should be visible
        self.assertIn("testuser", log_call_args)

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_empty_string_handling(self, mock_print, mock_logger):
        """Test handling of empty strings from environment variables."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # Test with all should flags disabled to avoid validation errors
        env_vars = {
            'GAME_NAME': '',  # Empty string should be converted appropriately  
            'SHOULD_PARSE': 'False',
            'SHOULD_PUSH_DATA': 'False'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = Options()
        
        # Empty strings should fallback to defaults for options with defaults
        self.assertEqual(options.game_name, "WRFrontiers")

    @patch.object(src_options, 'logger')
    @patch('builtins.print')
    def test_options_process_schema_method(self, mock_print, mock_logger):
        """Test the _process_schema method functionality."""
        mock_logger.add = Mock()
        mock_logger.remove = Mock()
        
        # Create a minimal test case with should flags disabled to avoid validation errors
        env_vars = {
            'SHOULD_PARSE': 'False',
            'SHOULD_PUSH_DATA': 'False'
        }
        args = create_args(log_level="WARNING")
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = Options(args)
        
        # Verify the method processed the schema correctly
        self.assertEqual(options.log_level, "WARNING")


if __name__ == '__main__':
    unittest.main()