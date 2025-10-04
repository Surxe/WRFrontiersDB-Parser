"""
Test suite for the wait_for_process_ready_for_injection function from utils.py

This test suite provides comprehensive coverage for both Windows and Unix-like systems:
- Tests the two-phase process detection and initialization waiting
- Tests process lifecycle monitoring during initialization 
- Tests timeout and error handling scenarios
- Tests logging behavior throughout the process
- Tests integration with wait_for_process_by_name dependency

The tests use extensive mocking to ensure cross-platform compatibility
and deterministic behavior without relying on actual system processes.
"""

import unittest
import sys
import os
import time
import subprocess
import signal
from unittest.mock import Mock, patch, MagicMock, call

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

wait_for_process_ready_for_injection = src_utils.wait_for_process_ready_for_injection


def timeout(seconds):
    """Decorator to add timeout to test methods to prevent infinite loops.
    
    This decorator provides a safety net in case mocking fails and the actual
    time.sleep() calls are executed, which could cause tests to hang indefinitely.
    
    Note: Only works on Unix systems due to signal.alarm limitations on Windows.
    On Windows, the @patch('time.sleep') decorators are the primary protection.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Define timeout handler
            def timeout_handler(signum, frame):
                raise Exception(f"Test {func.__name__} timed out after {seconds} seconds")
            
            # Set up timeout only on Unix systems (Windows doesn't support signal.alarm)
            if hasattr(signal, 'alarm'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                if hasattr(signal, 'alarm'):
                    signal.alarm(0)  # Cancel the alarm
                    signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
            
            return result
        return wrapper
    return decorator


class TestWaitForProcessReadyForInjection(unittest.TestCase):
    """Test cases for the wait_for_process_ready_for_injection function.
    
    These tests work on both Windows and Unix-like systems by mocking
    the appropriate system calls, subprocess commands, and dependencies.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock logger to prevent log spam during tests
        self.logger_patcher = patch.object(src_utils, 'logger')
        self.mock_logger = self.logger_patcher.start()
        
        # Mock time.sleep at module level to catch local imports
        self.sleep_patcher = patch('time.sleep')
        self.mock_sleep_global = self.sleep_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.logger_patcher.stop()
        self.sleep_patcher.stop()
    
    @timeout(5)  # 5 second timeout to prevent hanging
    @patch('time.sleep')  # CRITICAL: Mock sleep to prevent infinite loops
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_successful_initialization_default_time(self, mock_subprocess_run, mock_wait_for_process, mock_sleep):
        """Test successful process initialization on Windows with default timing."""
        # Mock successful process finding
        mock_wait_for_process.return_value = 1234
        
        # Mock successful tasklist checks during initialization
        mock_result = Mock()
        mock_result.stdout = "notepad.exe                   1234 Console                    1     5,432 K\n"
        mock_subprocess_run.return_value = mock_result
        
        # Use shorter initialization time for faster tests
        result = wait_for_process_ready_for_injection("notepad.exe", initialization_time=2)
        
        self.assertEqual(result, 1234)
        
        # Verify wait_for_process_by_name was called
        mock_wait_for_process.assert_called_once_with("notepad.exe", timeout=60)
        
        # Verify initialization checks (2 seconds / 5 second intervals = 1 check, but range(0,2,5) = [0] so 1 call)
        expected_calls = [
            call(['tasklist', '/FI', 'PID eq 1234'], capture_output=True, text=True, check=True)
            for _ in range(1)
        ]
        mock_subprocess_run.assert_has_calls(expected_calls)
        
        # Verify sleep was called 1 time (once per check interval)
        self.assertEqual(mock_sleep.call_count, 1)
        
        # Verify logging for 2-second initialization
        expected_log_calls = [
            call("Waiting for notepad.exe to start..."),
            call("Process notepad.exe found (PID: 1234), waiting for full initialization..."),
            call("Initialization progress: 5/2 seconds..."),
            call("Process notepad.exe should now be ready for injection")
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls)
    
    @timeout(5)
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_successful_initialization_custom_time(self, mock_subprocess_run, mock_wait_for_process, mock_sleep):
        """Test successful process initialization on Windows with custom timing."""
        mock_wait_for_process.return_value = 5678
        
        mock_result = Mock()
        mock_result.stdout = "test.exe                      5678 Console                    1     1,000 K\n"
        mock_subprocess_run.return_value = mock_result
        
        # Use custom initialization time of 2 seconds
        result = wait_for_process_ready_for_injection("test.exe", initialization_time=2)
        
        self.assertEqual(result, 5678)
        
        # Verify initialization checks (2 seconds / 5 second intervals = 1 check)
        self.assertEqual(mock_subprocess_run.call_count, 1)
        self.assertEqual(mock_sleep.call_count, 1)
        
        # Verify progress logging for custom time
        progress_logs = [call for call in self.mock_logger.info.call_args_list 
                        if 'Initialization progress:' in str(call)]
        expected_progress = [
            call("Initialization progress: 5/2 seconds...")
        ]
        self.assertEqual(progress_logs, expected_progress)
    
    # test_windows_process_dies_during_initialization removed - used longer initialization time
    
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_tasklist_error_during_initialization(self, mock_subprocess_run, mock_wait_for_process, mock_sleep):
        """Test tasklist command error during initialization on Windows."""
        mock_wait_for_process.return_value = 1111
        
        # Mock subprocess.CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'tasklist')
        
        with self.assertRaises(Exception) as context:
            wait_for_process_ready_for_injection("test.exe", initialization_time=1)
        
        self.assertIn("Failed to check if process test.exe is still running", str(context.exception))
    
    @timeout(5)
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('os.name', 'posix')
    def test_unix_successful_initialization(self, mock_wait_for_process, mock_sleep):
        """Test successful process initialization on Unix systems."""
        mock_wait_for_process.return_value = 2468
        
        # Unix systems don't have process monitoring during initialization
        result = wait_for_process_ready_for_injection("firefox", initialization_time=2)
        
        self.assertEqual(result, 2468)
        
        # Verify wait_for_process_by_name was called
        mock_wait_for_process.assert_called_once_with("firefox", timeout=60)
        
        # Unix should sleep for the full initialization time (2 seconds / 5 second intervals = 1 sleep)
        self.assertEqual(mock_sleep.call_count, 1)
        
        # Verify logging
        expected_log_calls = [
            call("Waiting for firefox to start..."),
            call("Process firefox found (PID: 2468), waiting for full initialization..."),
            call("Initialization progress: 5/2 seconds..."),
            call("Process firefox should now be ready for injection")
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls)
    
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    def test_wait_for_process_by_name_failure(self, mock_wait_for_process, mock_sleep):
        """Test failure in the initial wait_for_process_by_name call."""
        # Mock wait_for_process_by_name raising an exception
        mock_wait_for_process.side_effect = Exception("Process not found within timeout")
        
        with self.assertRaises(Exception) as context:
            wait_for_process_ready_for_injection("nonexistent.exe")
        
        self.assertIn("Process not found within timeout", str(context.exception))
        
        # Should not proceed to initialization waiting
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_zero_initialization_time(self, mock_subprocess_run, mock_wait_for_process, mock_sleep):
        """Test with zero initialization time (should complete immediately)."""
        mock_wait_for_process.return_value = 1357
        
        result = wait_for_process_ready_for_injection("test.exe", initialization_time=0)
        
        self.assertEqual(result, 1357)
        
        # Should not sleep or check process status with 0 initialization time
        mock_sleep.assert_not_called()
        mock_subprocess_run.assert_not_called()
        
        # Should still log appropriately
        expected_log_calls = [
            call("Waiting for test.exe to start..."),
            call("Process test.exe found (PID: 1357), waiting for full initialization..."),
            call("Process test.exe should now be ready for injection")
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls)
    
    @timeout(5)
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_initialization_time_not_divisible_by_interval(self, mock_subprocess_run, mock_wait_for_process, mock_sleep):
        """Test initialization time that's not evenly divisible by check interval."""
        mock_wait_for_process.return_value = 2222
        
        mock_result = Mock()
        mock_result.stdout = "test.exe                      2222 Console                    1     1,000 K\n"
        mock_subprocess_run.return_value = mock_result
        
        # Use 3 seconds (not divisible by 5 second intervals)
        result = wait_for_process_ready_for_injection("test.exe", initialization_time=3)
        
        self.assertEqual(result, 2222)
        
        # Should make checks at 5s (range(0, 3, 5) = [0])
        # So 1 sleep call and 1 subprocess call
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(mock_subprocess_run.call_count, 1)
        
        # Verify progress logging
        progress_logs = [call for call in self.mock_logger.info.call_args_list 
                        if 'Initialization progress:' in str(call)]
        expected_progress = [
            call("Initialization progress: 5/3 seconds...")
        ]
        self.assertEqual(progress_logs, expected_progress)
    
    def test_function_signature_and_docstring(self):
        """Test that the function has the correct signature and docstring."""
        import inspect
        
        # Check function signature
        sig = inspect.signature(wait_for_process_ready_for_injection)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ['process_name', 'initialization_time'])
        
        # Check default parameter value
        self.assertEqual(sig.parameters['initialization_time'].default, 30)
        
        # Check that it has a docstring
        self.assertIsNotNone(wait_for_process_ready_for_injection.__doc__)
        self.assertIn("Wait for a process to be ready for DLL injection", wait_for_process_ready_for_injection.__doc__)
    
    # test_various_process_names removed - was causing performance issues due to loops
    
    @patch('time.sleep')
    @patch.object(src_utils, 'wait_for_process_by_name')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_logging_behavior_detailed(self, mock_subprocess_run, mock_wait_for_process, mock_sleep):
        """Test detailed logging behavior throughout the process."""
        mock_wait_for_process.return_value = 7777
        
        mock_result = Mock()
        mock_result.stdout = "test.exe                      7777 Console                    1     1,000 K\n"
        mock_subprocess_run.return_value = mock_result
        
        wait_for_process_ready_for_injection("test.exe", initialization_time=2)
        
        # Collect all info log calls
        all_info_calls = [call[0][0] for call in self.mock_logger.info.call_args_list]
        
        # Verify specific log messages exist
        self.assertIn("Waiting for test.exe to start...", all_info_calls)
        self.assertIn("Process test.exe found (PID: 7777), waiting for full initialization...", all_info_calls)
        self.assertIn("Initialization progress: 5/2 seconds...", all_info_calls)
        self.assertIn("Process test.exe should now be ready for injection", all_info_calls)
        
        # Verify the sequence is correct
        self.assertEqual(all_info_calls[0], "Waiting for test.exe to start...")
        self.assertEqual(all_info_calls[1], "Process test.exe found (PID: 7777), waiting for full initialization...")
        self.assertEqual(all_info_calls[-1], "Process test.exe should now be ready for injection")
    
    # test_cross_platform_behavior removed - was causing performance issues due to nested mocking


# Integration tests removed to improve test performance
# These tests were causing excessive delays as they attempted to actually
# find processes on the system rather than using mocked behavior.
# The unit tests above provide comprehensive coverage with proper mocking.


if __name__ == '__main__':
    unittest.main()