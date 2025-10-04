"""
Test suite for the terminate_process_by_name function from utils.py

This test suite provides comprehensive coverage for both Windows and Unix-like systems:
- Tests process termination via taskkill (Windows) and pkill (Unix)
- Tests success and failure scenarios
- Tests error handling and return values
- Tests logging behavior
- Includes optional integration tests with real processes

The tests use extensive mocking to ensure cross-platform compatibility
and deterministic behavior without actually terminating system processes.
"""

import unittest
import sys
import os
import subprocess
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

terminate_process_by_name = src_utils.terminate_process_by_name


class TestTerminateProcessByName(unittest.TestCase):
    """Test cases for the terminate_process_by_name function.
    
    These tests work on both Windows and Unix-like systems by mocking
    the appropriate system calls and subprocess commands.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock logger to prevent log spam during tests
        self.logger_patcher = patch.object(src_utils, 'logger')
        self.mock_logger = self.logger_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.logger_patcher.stop()
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_terminate_success(self, mock_subprocess_run):
        """Test successful process termination on Windows."""
        # Mock successful taskkill output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = terminate_process_by_name("notepad.exe")
        
        self.assertTrue(result)
        mock_subprocess_run.assert_called_once_with(
            ['taskkill', '/F', '/IM', 'notepad.exe'],
            capture_output=True, text=True
        )
        self.mock_logger.info.assert_called_once_with("Terminated process notepad.exe")
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_terminate_failure_nonzero_return(self, mock_subprocess_run):
        """Test process termination failure with non-zero return code on Windows."""
        # Mock failed taskkill output
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: The process \"nonexistent.exe\" not found."
        mock_subprocess_run.return_value = mock_result
        
        result = terminate_process_by_name("nonexistent.exe")
        
        self.assertFalse(result)
        mock_subprocess_run.assert_called_once_with(
            ['taskkill', '/F', '/IM', 'nonexistent.exe'],
            capture_output=True, text=True
        )
        self.mock_logger.warning.assert_called_once_with(
            'Failed to terminate nonexistent.exe: ERROR: The process "nonexistent.exe" not found.'
        )
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_terminate_exception_handling(self, mock_subprocess_run):
        """Test exception handling during process termination on Windows."""
        # Mock subprocess.CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'taskkill')
        
        result = terminate_process_by_name("test.exe")
        
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_once()
        warning_call = self.mock_logger.warning.call_args[0][0]
        self.assertIn("Error terminating test.exe:", warning_call)
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_terminate_success(self, mock_subprocess_run):
        """Test successful process termination on Unix systems."""
        # Mock successful pkill output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = terminate_process_by_name("firefox")
        
        self.assertTrue(result)
        mock_subprocess_run.assert_called_once_with(
            ['pkill', '-f', 'firefox'],
            capture_output=True, text=True
        )
        self.mock_logger.info.assert_called_once_with("Terminated process firefox")
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_terminate_failure_nonzero_return(self, mock_subprocess_run):
        """Test process termination failure with non-zero return code on Unix systems."""
        # Mock failed pkill output (pkill returns 1 when no processes match)
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = terminate_process_by_name("nonexistent")
        
        self.assertFalse(result)
        mock_subprocess_run.assert_called_once_with(
            ['pkill', '-f', 'nonexistent'],
            capture_output=True, text=True
        )
        self.mock_logger.warning.assert_called_once_with("Failed to terminate nonexistent")
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_terminate_exception_handling(self, mock_subprocess_run):
        """Test exception handling during process termination on Unix systems."""
        # Mock subprocess.CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'pkill')
        
        result = terminate_process_by_name("test")
        
        self.assertFalse(result)
        self.mock_logger.warning.assert_called_once()
        warning_call = self.mock_logger.warning.call_args[0][0]
        self.assertIn("Error terminating test:", warning_call)
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_various_process_names(self, mock_subprocess_run):
        """Test terminating various process names on Windows."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        test_processes = [
            "notepad.exe",
            "WRFrontiers-Win64-Shipping.exe",
            "chrome.exe",
            "process_with_spaces.exe"
        ]
        
        for process_name in test_processes:
            with self.subTest(process_name=process_name):
                result = terminate_process_by_name(process_name)
                self.assertTrue(result)
        
        # Verify all processes were called with correct parameters
        expected_calls = [
            unittest.mock.call(['taskkill', '/F', '/IM', name], capture_output=True, text=True)
            for name in test_processes
        ]
        mock_subprocess_run.assert_has_calls(expected_calls)
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_various_process_names(self, mock_subprocess_run):
        """Test terminating various process names on Unix systems."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        test_processes = [
            "firefox",
            "vim",
            "python3",
            "process-with-dashes",
            "/usr/bin/some_program"
        ]
        
        for process_name in test_processes:
            with self.subTest(process_name=process_name):
                result = terminate_process_by_name(process_name)
                self.assertTrue(result)
        
        # Verify all processes were called with correct parameters
        expected_calls = [
            unittest.mock.call(['pkill', '-f', name], capture_output=True, text=True)
            for name in test_processes
        ]
        mock_subprocess_run.assert_has_calls(expected_calls)
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_empty_process_name(self, mock_subprocess_run):
        """Test terminating empty process name on Windows."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: Invalid argument/option - ''."
        mock_subprocess_run.return_value = mock_result
        
        result = terminate_process_by_name("")
        
        self.assertFalse(result)
        mock_subprocess_run.assert_called_once_with(
            ['taskkill', '/F', '/IM', ''],
            capture_output=True, text=True
        )
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_empty_process_name(self, mock_subprocess_run):
        """Test terminating empty process name on Unix systems."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = terminate_process_by_name("")
        
        self.assertFalse(result)
        mock_subprocess_run.assert_called_once_with(
            ['pkill', '-f', ''],
            capture_output=True, text=True
        )
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_special_characters_in_process_name(self, mock_subprocess_run):
        """Test terminating process with special characters on Windows."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        special_names = [
            "app&service.exe",
            "test(1).exe",
            "my-app_v2.exe",
            "üñíçödé.exe"
        ]
        
        for process_name in special_names:
            with self.subTest(process_name=process_name):
                result = terminate_process_by_name(process_name)
                self.assertTrue(result)
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_special_characters_in_process_name(self, mock_subprocess_run):
        """Test terminating process with special characters on Unix systems."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        special_names = [
            "app&service",
            "test(1)",
            "my-app_v2",
            "/path/to/app with spaces"
        ]
        
        for process_name in special_names:
            with self.subTest(process_name=process_name):
                result = terminate_process_by_name(process_name)
                self.assertTrue(result)
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_logging_behavior_success(self, mock_subprocess_run):
        """Test logging behavior on successful termination on Windows."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        terminate_process_by_name("test.exe")
        
        # Verify info log was called
        self.mock_logger.info.assert_called_once_with("Terminated process test.exe")
        # Verify warning log was not called
        self.mock_logger.warning.assert_not_called()
    
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_logging_behavior_failure(self, mock_subprocess_run):
        """Test logging behavior on failed termination on Windows."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Process not found"
        mock_subprocess_run.return_value = mock_result
        
        terminate_process_by_name("test.exe")
        
        # Verify warning log was called
        self.mock_logger.warning.assert_called_once_with("Failed to terminate test.exe: Process not found")
        # Verify info log was not called
        self.mock_logger.info.assert_not_called()
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_logging_behavior_success(self, mock_subprocess_run):
        """Test logging behavior on successful termination on Unix systems."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        terminate_process_by_name("test")
        
        # Verify info log was called
        self.mock_logger.info.assert_called_once_with("Terminated process test")
        # Verify warning log was not called
        self.mock_logger.warning.assert_not_called()
    
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_logging_behavior_failure(self, mock_subprocess_run):
        """Test logging behavior on failed termination on Unix systems."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result
        
        terminate_process_by_name("test")
        
        # Verify warning log was called
        self.mock_logger.warning.assert_called_once_with("Failed to terminate test")
        # Verify info log was not called
        self.mock_logger.info.assert_not_called()
    
    def test_function_signature_and_docstring(self):
        """Test that the function has the correct signature and docstring."""
        import inspect
        
        # Check function signature
        sig = inspect.signature(terminate_process_by_name)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ['process_name'])
        
        # Check that it has a docstring
        self.assertIsNotNone(terminate_process_by_name.__doc__)
        self.assertIn("Terminate a process by name", terminate_process_by_name.__doc__)
    
    @patch('subprocess.run')
    def test_cross_platform_behavior_switching(self, mock_subprocess_run):
        """Test that the function uses correct commands for different OS."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        # Test Windows behavior
        with patch('os.name', 'nt'):
            terminate_process_by_name("test.exe")
            mock_subprocess_run.assert_called_with(
                ['taskkill', '/F', '/IM', 'test.exe'],
                capture_output=True, text=True
            )
        
        mock_subprocess_run.reset_mock()
        
        # Test Unix behavior
        with patch('os.name', 'posix'):
            terminate_process_by_name("test")
            mock_subprocess_run.assert_called_with(
                ['pkill', '-f', 'test'],
                capture_output=True, text=True
            )


class TestTerminateProcessByNameIntegration(unittest.TestCase):
    """Integration tests that may interact with real system processes (optional, may be skipped)."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock logger to reduce noise
        self.logger_patcher = patch.object(src_utils, 'logger')
        self.mock_logger = self.logger_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.logger_patcher.stop()
    
    @unittest.skipUnless(os.name == 'nt', "Windows-specific integration test")
    def test_windows_terminate_nonexistent_process_integration(self):
        """Integration test trying to terminate a non-existent process on Windows."""
        # This should safely fail without side effects
        result = terminate_process_by_name("definitely_nonexistent_process_12345.exe")
        self.assertFalse(result)
        # Should log a warning
        self.mock_logger.warning.assert_called_once()
    
    @unittest.skipUnless(os.name == 'posix', "Unix-specific integration test")
    def test_unix_terminate_nonexistent_process_integration(self):
        """Integration test trying to terminate a non-existent process on Unix systems."""
        # This should safely fail without side effects
        result = terminate_process_by_name("definitely_nonexistent_process_12345")
        self.assertFalse(result)
        # Should log a warning
        self.mock_logger.warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()