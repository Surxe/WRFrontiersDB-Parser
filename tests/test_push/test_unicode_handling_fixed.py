"""
Simple Unicode handling tests for the push module.
"""
import unittest
import sys
import os
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the src directory to the Python path to import push module
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import the push module using proper import
try:
    from push.push import run_git_command
except ImportError:
    # Skip these tests if we can't import
    run_git_command = None


class TestUnicodeHandling(unittest.TestCase):
    """Test cases specifically for Unicode character handling in push module."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unittest.skipIf(run_git_command is None, "Could not import push module")
    @patch('push.push.subprocess.run')
    def test_run_git_command_cyrillic_characters(self, mock_subprocess_run):
        """Test that Cyrillic characters are handled properly."""
        # Mock subprocess result with Cyrillic characters
        mock_result = Mock()
        mock_result.stdout = 'Bot names: ["TestBot", "АхиллесСын", "Большой-КВА", "ЗНАК-СВЫШЕ"]'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        # Test the function
        result = run_git_command(['git', 'show', 'HEAD:current/BotNames.json'], cwd=self.temp_dir)
        
        # Verify subprocess was called with UTF-8 encoding
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        
        self.assertEqual(call_args[1]['encoding'], 'utf-8')
        self.assertEqual(call_args[1]['errors'], 'ignore')
        self.assertEqual(result.stdout, 'Bot names: ["TestBot", "АхиллесСын", "Большой-КВА", "ЗНАК-СВЫШЕ"]')

    @unittest.skipIf(run_git_command is None, "Could not import push module")
    @patch('push.push.subprocess.run')
    def test_run_git_command_unicode_decode_error_ignored(self, mock_subprocess_run):
        """Test that Unicode decode errors are ignored gracefully."""
        # Mock subprocess result
        mock_result = Mock()
        mock_result.stdout = "Successfully handled problematic Unicode content"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        # Test the function
        result = run_git_command(['git', 'log', '--oneline'], cwd=self.temp_dir)
        
        # Verify subprocess was called with error handling
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        
        self.assertEqual(call_args[1]['encoding'], 'utf-8')
        self.assertEqual(call_args[1]['errors'], 'ignore')
        self.assertEqual(result.stdout, "Successfully handled problematic Unicode content")

    @unittest.skipIf(run_git_command is None, "Could not import push module")  
    @patch('push.push.subprocess.run')
    def test_mixed_ascii_cyrillic_content(self, mock_subprocess_run):
        """Test mixed ASCII and Cyrillic content handling."""
        # Create content that mixes ASCII and Cyrillic
        mixed_content = """
        {
            "bots": [
                {"name": "TestBot", "type": "normal"},
                {"name": "АхиллесСын", "type": "special"}, 
                {"name": "NormalBot", "type": "normal"},
                {"name": "ЗНАК-СВЫШЕ", "type": "legendary"}
            ]
        }
        """
        
        mock_result = Mock()
        mock_result.stdout = mixed_content
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        # Test the function
        result = run_git_command(['git', 'show', 'HEAD:current/BotNames.json'], cwd=self.temp_dir)
        
        # Should handle mixed content without issues
        self.assertEqual(result.stdout, mixed_content)
        
        # Verify proper encoding settings
        call_args = mock_subprocess_run.call_args
        self.assertEqual(call_args[1]['encoding'], 'utf-8')
        self.assertEqual(call_args[1]['errors'], 'ignore')

    def test_unicode_in_file_paths(self):
        """Test that Unicode characters in file paths are handled correctly."""
        # This is a simple test that doesn't require subprocess mocking
        if run_git_command is None:
            self.skipTest("Could not import push module")
            
        # Create a test file with Unicode name
        unicode_file = os.path.join(self.temp_dir, "тест_файл.txt")
        
        try:
            with open(unicode_file, 'w', encoding='utf-8') as f:
                f.write("Test content with Cyrillic: Привет мир!")
            
            # File should exist and be readable
            self.assertTrue(os.path.exists(unicode_file))
            
            with open(unicode_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("Привет мир!", content)
                
        except (OSError, UnicodeError) as e:
            self.skipTest(f"System doesn't support Unicode filenames: {e}")

    def test_environment_variables_with_unicode(self):
        """Test that environment variables with Unicode content are handled."""
        if run_git_command is None:
            self.skipTest("Could not import push module")
            
        # Test that the function can handle Unicode in environment variables
        with patch('push.push.os.environ') as mock_environ:
            mock_environ.copy.return_value = {
                'PATH': '/usr/bin',
                'GIT_AUTHOR_NAME': 'Тест Юзер',  # Cyrillic name
                'GIT_AUTHOR_EMAIL': 'test@example.com'
            }
            
            with patch('push.push.subprocess.run') as mock_run:
                mock_result = Mock()
                mock_result.stdout = "Success"
                mock_result.returncode = 0
                mock_run.return_value = mock_result
                
                # This should not raise any encoding errors
                run_git_command(['git', 'status'], cwd=self.temp_dir)
                
                # Verify the environment was set correctly
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                env = call_args[1]['env']
                
                # Environment should contain the Unicode name
                self.assertIn('GIT_AUTHOR_NAME', env)


if __name__ == '__main__':
    unittest.main(verbosity=2)