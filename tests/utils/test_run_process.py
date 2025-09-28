import unittest
import sys
import os
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

run_process = src_utils.run_process


class TestRunProcess(unittest.TestCase):
    """Test cases for the run_process function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the logger to capture log calls
        self.logger_patcher = patch.object(src_utils, 'logger')
        self.mock_logger = self.logger_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.logger_patcher.stop()
    
    @patch('subprocess.Popen')
    def test_successful_process_with_string_command(self, mock_popen):
        """Test successful execution with string command."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, None, 0]  # Running, then finished
        mock_process.stdout.__enter__ = Mock(return_value=mock_process.stdout)
        mock_process.stdout.__exit__ = Mock(return_value=None)
        mock_process.stdout.readline.side_effect = ["line1\n", "line2\n", "line3\n", ""]
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute
        run_process("echo hello", name="test_process")
        
        # Verify subprocess.Popen was called correctly
        mock_popen.assert_called_once_with(
            "echo hello",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Verify logger calls
        expected_calls = [
            call.trace('[process: test_process] line1'),
            call.trace('[process: test_process] line2'),
            call.trace('[process: test_process] line3')
        ]
        self.mock_logger.trace.assert_has_calls(expected_calls)
        
        # Verify wait was called
        mock_process.wait.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_successful_process_with_list_command(self, mock_popen):
        """Test successful execution with list command."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]  # Running, then finished
        mock_process.stdout.__enter__ = Mock(return_value=mock_process.stdout)
        mock_process.stdout.__exit__ = Mock(return_value=None)
        mock_process.stdout.readline.side_effect = ["output line\n", ""]
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute
        run_process(["ls", "-l"], name="list_files")
        
        # Verify subprocess.Popen was called correctly
        mock_popen.assert_called_once_with(
            ["ls", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Verify logger was called
        self.mock_logger.trace.assert_called_with('[process: list_files] output line')
    
    @patch('subprocess.Popen')
    def test_process_without_name(self, mock_popen):
        """Test process execution without specifying a name."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.side_effect = [None, 0]  # Running, then finished
        mock_process.stdout.__enter__ = Mock(return_value=mock_process.stdout)
        mock_process.stdout.__exit__ = Mock(return_value=None)
        mock_process.stdout.readline.side_effect = ["test output\n", ""]
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute without name parameter
        run_process("echo test")
        
        # Verify logger was called with empty name
        self.mock_logger.trace.assert_called_with('[process: ] test output')
    
    @patch('subprocess.Popen')
    def test_process_with_empty_output(self, mock_popen):
        """Test process that produces no output."""
        # Setup mock process with no output
        mock_process = Mock()
        mock_process.stdout = StringIO("")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute
        run_process("true", name="silent_process")
        
        # Verify no trace calls were made
        self.mock_logger.trace.assert_not_called()
    
    @patch('subprocess.Popen')
    def test_process_with_multiline_output(self, mock_popen):
        """Test process with multiple lines of output."""
        # Setup mock process with multiline output
        mock_process = Mock()
        mock_process.stdout = StringIO("Line 1\nLine 2 with spaces\nLine 3\n\nLine 5\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute
        run_process("multi_line_command", name="multi")
        
        # Verify all lines were logged (including empty line)
        expected_calls = [
            call.trace('[process: multi] Line 1'),
            call.trace('[process: multi] Line 2 with spaces'),
            call.trace('[process: multi] Line 3'),
            call.trace('[process: multi] '),  # Empty line
            call.trace('[process: multi] Line 5')
        ]
        self.mock_logger.trace.assert_has_calls(expected_calls)
    
    @patch('subprocess.Popen')
    def test_process_failure_non_zero_exit_code(self, mock_popen):
        """Test process that exits with non-zero code."""
        # Setup mock process that fails
        mock_process = Mock()
        mock_process.stdout = StringIO("error output\n")
        mock_process.wait.return_value = 1  # Non-zero exit code
        mock_popen.return_value = mock_process
        
        # Execute and expect exception
        with self.assertRaises(Exception) as cm:
            run_process("failing_command", name="fail_test")
        
        # Verify exception message
        self.assertEqual(str(cm.exception), "Process fail_test exited with code 1")
        
        # Verify output was still logged
        self.mock_logger.trace.assert_called_with('[process: fail_test] error output')
    
    @patch('subprocess.Popen')
    def test_process_failure_different_exit_codes(self, mock_popen):
        """Test process failures with different exit codes."""
        # Test exit code 2
        mock_process_2 = Mock()
        mock_process_2.stdout = StringIO("")
        mock_process_2.wait.return_value = 2
        mock_popen.return_value = mock_process_2
        
        with self.assertRaises(Exception) as cm:
            run_process("command", name="test")
        self.assertEqual(str(cm.exception), "Process test exited with code 2")
        
        # Test exit code 255 - create a new mock object
        mock_process_255 = Mock()
        mock_process_255.stdout = StringIO("")
        mock_process_255.wait.return_value = 255
        mock_popen.return_value = mock_process_255
        
        with self.assertRaises(Exception) as cm:
            run_process("command", name="test")
        self.assertEqual(str(cm.exception), "Process test exited with code 255")
    
    @patch('subprocess.Popen')
    def test_popen_constructor_exception(self, mock_popen):
        """Test exception during subprocess creation."""
        # Setup Popen to raise an exception
        mock_popen.side_effect = FileNotFoundError("Command not found")
        
        # Execute and expect exception
        with self.assertRaises(Exception) as cm:
            run_process("nonexistent_command", name="test_error")
        
        # Verify exception message - Exception with 2 args creates a tuple representation
        self.assertIn("Failed to run test_error process", str(cm.exception))
    
    @patch('time.time')
    @patch('time.sleep')  # Mock sleep to speed up test
    @patch('subprocess.Popen')
    def test_process_timeout(self, mock_popen, mock_sleep, mock_time):
        """Test process that times out."""
        # Setup mock process that never finishes
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process never finishes
        mock_process.stdout.__enter__ = Mock(return_value=mock_process.stdout)
        mock_process.stdout.__exit__ = Mock(return_value=None)
        mock_process.stdout.readline.return_value = ""  # No output
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process
        
        # Create a counter to simulate increasing time
        time_counter = [0]
        def mock_time_func():
            time_counter[0] += 1
            if time_counter[0] == 1:
                return 0  # start_time
            elif time_counter[0] == 2:
                return 150  # first check - still within timeout
            else:
                return 301  # subsequent checks - timeout exceeded
        
        mock_time.side_effect = mock_time_func
        
        # Execute with short timeout and expect exception
        with self.assertRaises(Exception) as cm:
            run_process("long_running_command", name="timeout_test", timeout=300)
        
        # Verify timeout exception message
        self.assertIn("timed out after 300 seconds", str(cm.exception))
        
        # Verify process was terminated (may be called twice - once for timeout, once for cleanup)
        self.assertTrue(mock_process.terminate.call_count >= 1)
    
    @patch('subprocess.Popen')
    def test_process_with_remaining_output_after_completion(self, mock_popen):
        """Test process that has remaining output after completion."""
        # Setup mock process that finishes with remaining output
        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]  # Running, running, then finished
        mock_process.stdout.__enter__ = Mock(return_value=mock_process.stdout)
        mock_process.stdout.__exit__ = Mock(return_value=None)
        mock_process.stdout.readline.return_value = ""  # No line-by-line output
        mock_process.stdout.read.return_value = "Final output line 1\nFinal output line 2\n"
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute
        run_process("command_with_final_output", name="final_output_test")
        
        # Verify final output was logged
        expected_calls = [
            call.trace('[process: final_output_test] Final output line 1'),
            call.trace('[process: final_output_test] Final output line 2')
        ]
        self.mock_logger.trace.assert_has_calls(expected_calls)
    
    @patch('subprocess.Popen')  
    def test_custom_timeout_parameter(self, mock_popen):
        """Test process with custom timeout parameter."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process finishes immediately
        mock_process.stdout.__enter__ = Mock(return_value=mock_process.stdout)
        mock_process.stdout.__exit__ = Mock(return_value=None)
        mock_process.stdout.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute with custom timeout (should work normally since process finishes quickly)
        run_process("quick_command", name="custom_timeout_test", timeout=60)
        
        # Verify process was called correctly
        mock_popen.assert_called_once()
        mock_process.wait.assert_called_once()
    
    @patch('os.name', 'nt')  # Mock Windows OS
    @patch('subprocess.Popen')
    def test_shell_script_on_windows_string_param(self, mock_popen):
        """Test shell script handling on Windows with string parameter."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = StringIO("script output\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute shell script on Windows
        run_process("script.sh", name="shell_test")
        
        # Verify bash was prepended
        mock_popen.assert_called_once_with(
            ['bash', 'script.sh'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    @patch('os.name', 'nt')  # Mock Windows OS
    @patch('subprocess.Popen')
    def test_shell_script_on_windows_list_param(self, mock_popen):
        """Test shell script handling on Windows with list parameter."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = StringIO("script with args\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute shell script with arguments on Windows
        run_process(["myscript.sh", "--arg1", "value"], name="shell_args")
        
        # Verify bash was prepended to the list
        mock_popen.assert_called_once_with(
            ['bash', 'myscript.sh', '--arg1', 'value'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    @patch('os.name', 'nt')  # Mock Windows OS
    @patch('subprocess.Popen')
    def test_non_shell_script_on_windows(self, mock_popen):
        """Test non-shell script commands on Windows (should not modify)."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = StringIO("regular command\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute regular command on Windows
        run_process("python script.py", name="python_test")
        
        # Verify command was not modified
        mock_popen.assert_called_once_with(
            "python script.py",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    @patch('os.name', 'posix')  # Mock Unix-like OS
    @patch('subprocess.Popen')
    def test_shell_script_on_unix(self, mock_popen):
        """Test shell script handling on Unix-like systems (should not modify)."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = StringIO("unix script\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute shell script on Unix
        run_process("script.sh", name="unix_shell")
        
        # Verify command was not modified
        mock_popen.assert_called_once_with(
            "script.sh",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    @patch('os.name', 'nt')  # Mock Windows OS
    @patch('subprocess.Popen')
    def test_empty_list_on_windows(self, mock_popen):
        """Test empty list parameter on Windows."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = StringIO("")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute with empty list
        run_process([], name="empty_list")
        
        # Verify command was not modified (empty list doesn't have [0] element)
        mock_popen.assert_called_once_with(
            [],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    @patch('os.name', 'nt')  # Mock Windows OS  
    @patch('subprocess.Popen')
    def test_list_with_non_shell_script_on_windows(self, mock_popen):
        """Test list with non-shell script first element on Windows."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = StringIO("python output\n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute with list starting with non-.sh command
        run_process(["python", "script.py", "--arg"], name="python_list")
        
        # Verify command was not modified
        mock_popen.assert_called_once_with(
            ["python", "script.py", "--arg"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    @patch('subprocess.Popen')
    def test_output_line_stripping(self, mock_popen):
        """Test that output lines are properly stripped of whitespace."""
        # Setup mock process with lines that have trailing whitespace
        mock_process = Mock()
        mock_process.stdout = StringIO("  line with spaces  \n\ttabbed line\t\n\n  \n")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Execute
        run_process("whitespace_test", name="strip_test")
        
        # Verify lines were stripped
        expected_calls = [
            call.trace('[process: strip_test] line with spaces'),
            call.trace('[process: strip_test] tabbed line'),
            call.trace('[process: strip_test] '),  # Empty line after stripping
            call.trace('[process: strip_test] ')   # Line with only whitespace, stripped to empty
        ]
        self.mock_logger.trace.assert_has_calls(expected_calls)
    
    def test_edge_case_inputs(self):
        """Test edge cases with various input types."""
        # Test with None name (should work, defaults to empty string)
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = StringIO("test\n")
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            # This should work with None name
            run_process("echo test", name=None)
            self.mock_logger.trace.assert_called_with('[process: None] test')


if __name__ == '__main__':
    unittest.main()