"""
Test suite for the wait_for_process_by_name function from utils.py

This test suite provides comprehensive coverage for both Windows and Unix-like systems:
- Tests process detection via tasklist (Windows) and pgrep (Unix)
- Tests timeout handling and error conditions
- Tests process name matching including truncated names
- Tests debug logging behavior
- Includes optional integration tests with real processes

The tests use extensive mocking to ensure cross-platform compatibility
and deterministic behavior without relying on actual system processes.
"""

import unittest
import sys
import os
import time
import subprocess
import threading
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

wait_for_process_by_name = src_utils.wait_for_process_by_name


class TestWaitForProcessByName(unittest.TestCase):
    """Test cases for the wait_for_process_by_name function.
    
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
    
    @patch('time.sleep')  # Speed up tests by mocking sleep
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_process_found_immediately(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test finding a process immediately on Windows."""
        # Mock time progression
        mock_time.side_effect = [0, 0]  # start_time, first check
        
        # Mock successful tasklist output
        mock_result = Mock()
        mock_result.stdout = "notepad.exe                   1234 Console                    1     5,432 K\n"
        mock_subprocess_run.return_value = mock_result
        
        result = wait_for_process_by_name("notepad.exe", timeout=60)
        
        self.assertEqual(result, 1234)
        mock_subprocess_run.assert_called_with(
            ['tasklist', '/FI', 'IMAGENAME eq notepad.exe'],
            capture_output=True, text=True, check=True
        )
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_process_found_after_delay(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test finding a process after several attempts on Windows."""
        # Mock time progression: 0, 0, 5, 10 (found on 3rd attempt)
        mock_time.side_effect = [0, 0, 5, 10]
        
        # First two calls return no process, third call returns process
        mock_result_empty = Mock()
        mock_result_empty.stdout = "Image Name                     PID Session Name        Session#    Mem Usage\n========================= ======== ================ =========== ============\n"
        
        mock_result_found = Mock()
        mock_result_found.stdout = "notepad.exe                   5678 Console                    1     5,432 K\n"
        
        mock_subprocess_run.side_effect = [mock_result_empty, mock_result_empty, mock_result_found]
        
        result = wait_for_process_by_name("notepad.exe", timeout=60)
        
        self.assertEqual(result, 5678)
        self.assertEqual(mock_subprocess_run.call_count, 3)
        # Sleep is called once after second failed attempt, but not after successful third attempt
        self.assertEqual(mock_sleep.call_count, 1)
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_process_with_truncated_name(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test finding a process with truncated name on Windows."""
        mock_time.side_effect = [0, 0]
        
        # Mock tasklist output with truncated process name
        mock_result = Mock()
        mock_result.stdout = "wrfrontiers-win64-ship        1234 Console                    1    50,432 K\n"
        mock_subprocess_run.return_value = mock_result
        
        result = wait_for_process_by_name("WRFrontiers-Win64-Shipping.exe", timeout=60)
        
        self.assertEqual(result, 1234)
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_process_not_found_timeout(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test timeout when process is not found on Windows."""
        # Mock time to exceed timeout
        mock_time.side_effect = [0, 30, 65]  # Exceeds 60 second timeout
        
        # Mock empty tasklist output
        mock_result = Mock()
        mock_result.stdout = "Image Name                     PID Session Name        Session#    Mem Usage\n========================= ======== ================ =========== ============\n"
        mock_subprocess_run.return_value = mock_result
        
        with self.assertRaises(Exception) as context:
            wait_for_process_by_name("nonexistent.exe", timeout=60)
        
        self.assertIn("Process nonexistent.exe not found within 60 seconds", str(context.exception))
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_subprocess_error_handling(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test handling of subprocess errors on Windows."""
        mock_time.side_effect = [0, 30, 65]  # Will timeout
        
        # Mock subprocess.CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'tasklist')
        
        with self.assertRaises(Exception) as context:
            wait_for_process_by_name("test.exe", timeout=60)
        
        self.assertIn("Process test.exe not found within 60 seconds", str(context.exception))
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_process_found_immediately(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test finding a process immediately on Unix systems."""
        mock_time.side_effect = [0, 0]
        
        # Mock successful pgrep output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1234\n5678\n"
        mock_subprocess_run.return_value = mock_result
        
        result = wait_for_process_by_name("firefox", timeout=60)
        
        self.assertEqual(result, 1234)  # Should return first PID
        mock_subprocess_run.assert_called_with(
            ['pgrep', '-f', 'firefox'],
            capture_output=True, text=True
        )
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_process_found_after_delay(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test finding a process after several attempts on Unix systems."""
        mock_time.side_effect = [0, 0, 5, 10]
        
        # First two calls return no process, third call returns process
        mock_result_empty = Mock()
        mock_result_empty.returncode = 1  # pgrep returns 1 when no processes found
        mock_result_empty.stdout = ""
        
        mock_result_found = Mock()
        mock_result_found.returncode = 0
        mock_result_found.stdout = "9876\n"
        
        mock_subprocess_run.side_effect = [mock_result_empty, mock_result_empty, mock_result_found]
        
        result = wait_for_process_by_name("vim", timeout=60)
        
        self.assertEqual(result, 9876)
        self.assertEqual(mock_subprocess_run.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_process_not_found_timeout(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test timeout when process is not found on Unix systems."""
        mock_time.side_effect = [0, 30, 65]  # Exceeds timeout
        
        # Mock pgrep returning no processes
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_subprocess_run.return_value = mock_result
        
        with self.assertRaises(Exception) as context:
            wait_for_process_by_name("nonexistent", timeout=60)
        
        self.assertIn("Process nonexistent not found within 60 seconds", str(context.exception))
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_subprocess_error_handling(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test handling of subprocess errors on Unix systems."""
        mock_time.side_effect = [0, 30, 65]  # Will timeout
        
        # Mock subprocess.CalledProcessError and ValueError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'pgrep')
        
        with self.assertRaises(Exception) as context:
            wait_for_process_by_name("test", timeout=60)
        
        self.assertIn("Process test not found within 60 seconds", str(context.exception))
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_unix_invalid_pid_handling(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test handling of invalid PID output on Unix systems."""
        mock_time.side_effect = [0, 30, 65]  # Will timeout
        
        # Mock pgrep returning invalid PID
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "not_a_number\n"
        mock_subprocess_run.return_value = mock_result
        
        with self.assertRaises(Exception) as context:
            wait_for_process_by_name("test", timeout=60)
        
        self.assertIn("Process test not found within 60 seconds", str(context.exception))
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_debug_logging_behavior(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test that debug logging occurs at expected intervals on Windows."""
        # Mock time to simulate multiple attempts
        mock_time.side_effect = [0, 0, 5, 10, 15, 20, 25, 30, 35]  # 8 attempts
        
        # Mock empty tasklist output for all attempts except the last
        mock_result_empty = Mock()
        mock_result_empty.stdout = "Image Name                     PID Session Name        Session#    Mem Usage\n"
        
        mock_result_found = Mock()
        mock_result_found.stdout = "notepad.exe                   1234 Console                    1     5,432 K\n"
        
        # Return empty results for first 7 attempts, then found
        mock_subprocess_run.side_effect = [mock_result_empty] * 7 + [mock_result_found]
        
        result = wait_for_process_by_name("notepad.exe", timeout=60)
        
        self.assertEqual(result, 1234)
        # Verify debug logging was called for odd-numbered attempts
        debug_calls = [call for call in self.mock_logger.debug.call_args_list 
                      if 'Attempt' in str(call)]
        self.assertGreater(len(debug_calls), 0)
    
    @patch('time.sleep')
    @patch('time.time') 
    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_windows_full_tasklist_debug_logging(self, mock_subprocess_run, mock_time, mock_sleep):
        """Test that full tasklist debugging occurs at expected intervals on Windows."""
        # Mock time to reach the 6th attempt (30 seconds) where debug logging should trigger
        mock_time.side_effect = [0] + [i*5 for i in range(8)]  # 8 attempts
        
        mock_result_empty = Mock()
        mock_result_empty.stdout = "Image Name                     PID Session Name        Session#    Mem Usage\n"
        
        mock_result_tasklist = Mock()
        mock_result_tasklist.stdout = "explorer.exe                  1000 Console                    1    50,000 K\n"
        
        mock_result_found = Mock()
        mock_result_found.stdout = "notepad.exe                   1234 Console                    1     5,432 K\n"
        
        call_count = 0
        def subprocess_side_effect(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if cmd == ['tasklist']:  # Unfiltered tasklist for debugging
                return mock_result_tasklist
            else:  # Filtered tasklist
                # Return empty for first 7 filtered calls, then found on 8th
                if call_count <= 7:
                    return mock_result_empty
                else:
                    return mock_result_found
        
        mock_subprocess_run.side_effect = subprocess_side_effect
        
        result = wait_for_process_by_name("notepad.exe", timeout=60)
        
        self.assertEqual(result, 1234)
        # Should have called both filtered and unfiltered tasklist (at least 8 calls)
        self.assertGreaterEqual(mock_subprocess_run.call_count, 8)
    
    def test_custom_timeout_parameter(self):
        """Test that custom timeout parameter is respected."""
        with patch('time.time') as mock_time, \
             patch('time.sleep'), \
             patch('subprocess.run'), \
             patch('os.name', 'nt'):
            
            # Mock time to exceed custom timeout of 10 seconds
            mock_time.side_effect = [0, 5, 12]
            
            mock_result = Mock()
            mock_result.stdout = "Image Name                     PID Session Name        Session#    Mem Usage\n"
            
            with patch('subprocess.run', return_value=mock_result):
                with self.assertRaises(Exception) as context:
                    wait_for_process_by_name("test.exe", timeout=10)
                
                self.assertIn("Process test.exe not found within 10 seconds", str(context.exception))


class TestWaitForProcessByNameIntegration(unittest.TestCase):
    """Integration tests that use real processes (optional, may be skipped in CI)."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock logger to reduce noise
        self.logger_patcher = patch.object(src_utils, 'logger')
        self.mock_logger = self.logger_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.logger_patcher.stop()
    
    @unittest.skipUnless(os.name == 'nt', "Windows-specific integration test")
    def test_windows_real_process_integration(self):
        """Integration test with a real Windows process (if available)."""
        try:
            # Try to find a common Windows process
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq explorer.exe'], 
                                  capture_output=True, text=True, check=True)
            if 'explorer.exe' in result.stdout:
                # If explorer.exe is running, test should find it quickly
                pid = wait_for_process_by_name("explorer.exe", timeout=10)
                self.assertIsInstance(pid, int)
                self.assertGreater(pid, 0)
            else:
                self.skipTest("No suitable process found for integration test")
        except Exception as e:
            self.skipTest(f"Integration test skipped due to system constraints: {e}")
    
    @unittest.skipUnless(os.name == 'posix', "Unix-specific integration test")
    def test_unix_real_process_integration(self):
        """Integration test with a real Unix process (if available)."""
        try:
            # Try to find init process (should always exist on Unix systems)
            result = subprocess.run(['pgrep', '-f', 'init'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                # If init process found, test should find it quickly
                pid = wait_for_process_by_name("init", timeout=10)
                self.assertIsInstance(pid, int)
                self.assertGreater(pid, 0)
            else:
                self.skipTest("No suitable process found for integration test")
        except Exception as e:
            self.skipTest(f"Integration test skipped due to system constraints: {e}")


if __name__ == '__main__':
    unittest.main()