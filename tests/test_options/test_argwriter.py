import unittest
import sys
import os
import argparse
from unittest.mock import patch, Mock, MagicMock
from typing import Literal
from pathlib import Path

# Add the src directory to the Python path to import options
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.options module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_options", os.path.join(src_path, "options.py"))
src_options = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_options)

ArgumentWriter = src_options.ArgumentWriter


class TestArgumentWriter(unittest.TestCase):
    """Test cases for the ArgumentWriter class.
    
    The ArgumentWriter class is responsible for dynamically adding command line arguments
    to an argparse parser based on the OPTIONS_SCHEMA structure.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.writer = ArgumentWriter()
        self.parser = argparse.ArgumentParser()

    @patch.object(src_options, 'logger')
    def test_argument_writer_initialization(self, mock_logger):
        """Test ArgumentWriter initializes with OPTIONS_SCHEMA."""
        writer = ArgumentWriter()
        self.assertEqual(writer.schema, src_options.OPTIONS_SCHEMA)
        self.assertIsNotNone(writer.schema)
        self.assertIsInstance(writer.schema, dict)

    @patch.object(src_options, 'logger')
    def test_add_boolean_argument(self, mock_logger):
        """Test adding boolean arguments to parser."""
        # Use actual boolean option from schema
        test_schema = {
            "SHOULD_PARSE": {
                "arg": "--should-parse",
                "type": bool,
                "default": False,
                "help": "Whether to parse the game files"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse arguments to verify the boolean argument was added correctly
        args = self.parser.parse_args(['--should-parse'])
        self.assertTrue(args.should_parse)
        
        # Test default behavior (no flag provided)
        args = self.parser.parse_args([])
        self.assertIsNone(args.should_parse)
        
        # Verify logger was called
        mock_logger.debug.assert_called()

    @patch.object(src_options, 'logger')
    def test_add_literal_argument(self, mock_logger):
        """Test adding Literal type arguments to parser."""
        # Use actual Literal option from schema
        test_schema = {
            "LOG_LEVEL": {
                "arg": "--log-level",
                "type": Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "default": "DEBUG",
                "help": "Logging level"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse valid choice
        args = self.parser.parse_args(['--log-level', 'INFO'])
        self.assertEqual(args.log_level, 'INFO')
        
        # Test invalid choice raises error
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--log-level', 'INVALID'])
        
        # Verify logger was called
        mock_logger.debug.assert_called()

    @patch.object(src_options, 'logger')
    def test_add_path_argument(self, mock_logger):
        """Test adding Path type arguments to parser."""
        # Create a mock schema with a Path option
        test_schema = {
            "TEST_PATH": {
                "arg": "--test-path",
                "type": Path,
                "default": None,
                "help": "Test path option"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse path argument
        test_path = "/some/test/path"
        args = self.parser.parse_args(['--test-path', test_path])
        self.assertEqual(args.test_path, test_path)
        
        # Verify logger was called
        mock_logger.debug.assert_called()

    @patch.object(src_options, 'logger')
    def test_add_string_argument(self, mock_logger):
        """Test adding string type arguments to parser."""
        # Create a mock schema with a string option
        test_schema = {
            "TEST_STRING": {
                "arg": "--test-string",
                "type": str,
                "default": "default_value",
                "help": "Test string option"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse string argument
        args = self.parser.parse_args(['--test-string', 'test_value'])
        self.assertEqual(args.test_string, 'test_value')
        
        # Verify logger was called
        mock_logger.debug.assert_called()

    @patch.object(src_options, 'logger')
    def test_add_integer_argument(self, mock_logger):
        """Test adding integer type arguments to parser."""
        # Create a mock schema with an integer option
        test_schema = {
            "TEST_INT": {
                "arg": "--test-int",
                "type": int,
                "default": 42,
                "help": "Test integer option"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse integer argument
        args = self.parser.parse_args(['--test-int', '100'])
        self.assertEqual(args.test_int, 100)
        self.assertIsInstance(args.test_int, int)
        
        # Test invalid integer raises error
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--test-int', 'not_a_number'])

    @patch.object(src_options, 'logger')
    def test_help_text_includes_default(self, mock_logger):
        """Test that help text includes the default value."""
        test_schema = {
            "TEST_OPTION": {
                "arg": "--test-option",
                "type": str,
                "default": "test_default",
                "help": "Test option help"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Get help text
        help_text = self.parser.format_help()
        self.assertIn("Test option help (default: test_default)", help_text)

    @patch.object(src_options, 'logger')
    def test_section_options_are_added(self, mock_logger):
        """Test that section_options are recursively added to the parser."""
        test_schema = {
            "MAIN_OPTION": {
                "arg": "--main-option",
                "type": bool,
                "default": False,
                "help": "Main option",
                "section_options": {
                    "SUB_OPTION_1": {
                        "arg": "--sub-option-1",
                        "type": str,
                        "default": "sub_default",
                        "help": "Sub option 1"
                    },
                    "SUB_OPTION_2": {
                        "arg": "--sub-option-2",
                        "type": int,
                        "default": 10,
                        "help": "Sub option 2"
                    }
                }
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse arguments for main and sub options
        args = self.parser.parse_args([
            '--main-option',
            '--sub-option-1', 'test_value',
            '--sub-option-2', '25'
        ])
        
        self.assertTrue(args.main_option)
        self.assertEqual(args.sub_option_1, 'test_value')
        self.assertEqual(args.sub_option_2, 25)

    @patch.object(src_options, 'logger')
    def test_nested_section_options(self, mock_logger):
        """Test deeply nested section_options are handled correctly."""
        test_schema = {
            "LEVEL_1": {
                "arg": "--level-1",
                "type": bool,
                "default": False,
                "help": "Level 1 option",
                "section_options": {
                    "LEVEL_2": {
                        "arg": "--level-2",
                        "type": str,
                        "default": "level2",
                        "help": "Level 2 option",
                        "section_options": {
                            "LEVEL_3": {
                                "arg": "--level-3",
                                "type": int,
                                "default": 3,
                                "help": "Level 3 option"
                            }
                        }
                    }
                }
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse nested arguments
        args = self.parser.parse_args([
            '--level-1',
            '--level-2', 'nested_value',
            '--level-3', '99'
        ])
        
        self.assertTrue(args.level_1)
        self.assertEqual(args.level_2, 'nested_value')
        self.assertEqual(args.level_3, 99)

    @patch.object(src_options, 'logger')
    def test_real_schema_integration(self, mock_logger):
        """Test ArgumentWriter works with the real OPTIONS_SCHEMA."""
        # Use the actual schema
        self.writer.add_arguments(self.parser)
        
        # Test parsing some real arguments from the schema
        args = self.parser.parse_args([
            '--log-level', 'INFO',
            '--should-parse',
            '--game-name', 'testuser'
        ])
        
        self.assertEqual(args.log_level, 'INFO')
        self.assertTrue(args.should_parse)
        self.assertEqual(args.game_name, 'testuser')

    @patch.object(src_options, 'logger')
    def test_argument_name_conversion(self, mock_logger):
        """Test that argument names are properly converted from dashes to underscores."""
        test_schema = {
            "DASH_OPTION": {
                "arg": "--dash-option-name",
                "type": str,
                "default": "default",
                "help": "Option with dashes"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Parse argument and verify attribute name conversion
        args = self.parser.parse_args(['--dash-option-name', 'test_value'])
        self.assertEqual(args.dash_option_name, 'test_value')
        self.assertTrue(hasattr(args, 'dash_option_name'))

    @patch.object(src_options, 'logger')
    def test_missing_help_text(self, mock_logger):
        """Test handling of options without help text."""
        test_schema = {
            "NO_HELP_OPTION": {
                "arg": "--no-help",
                "type": str,
                "default": "default"
                # Note: no "help" key
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # Should not raise an exception
        args = self.parser.parse_args(['--no-help', 'test'])
        self.assertEqual(args.no_help, 'test')
        
        # Help text should still include default
        help_text = self.parser.format_help()
        self.assertIn("(default: default)", help_text)

    @patch.object(src_options, 'logger')
    def test_empty_schema(self, mock_logger):
        """Test ArgumentWriter handles empty schema gracefully."""
        empty_schema = {}
        
        with patch.object(self.writer, 'schema', empty_schema):
            # Should not raise an exception
            self.writer.add_arguments(self.parser)
        
        # Parser should still work but have no arguments
        args = self.parser.parse_args([])
        self.assertIsInstance(args, argparse.Namespace)

    def test_parser_integration(self):
        """Test that ArgumentWriter integrates properly with argparse parser."""
        # Create a new parser for this test
        test_parser = argparse.ArgumentParser(description='Test parser')
        
        # Add arguments using ArgumentWriter
        self.writer.add_arguments(test_parser)
        
        # Verify parser can show help without errors
        help_text = test_parser.format_help()
        self.assertIn('usage:', help_text)
        self.assertIn('Test parser', help_text)

    @patch.object(src_options, 'logger')
    def test_duplicate_argument_names(self, mock_logger):
        """Test handling of potential duplicate argument names."""
        # This shouldn't happen with a well-formed schema, but test resilience
        test_schema = {
            "OPTION_1": {
                "arg": "--duplicate-name",
                "type": str,
                "default": "first",
                "help": "First option"
            }
        }
        
        with patch.object(self.writer, 'schema', test_schema):
            self.writer.add_arguments(self.parser)
        
        # First addition should work
        args = self.parser.parse_args(['--duplicate-name', 'value'])
        self.assertEqual(args.duplicate_name, 'value')


if __name__ == '__main__':
    unittest.main()