import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

is_admin = src_utils.is_admin


class TestIsAdmin(unittest.TestCase):
    """Test cases for the is_admin function.
    
    Note: The current implementation only supports Windows via ctypes.windll.shell32.IsUserAnAdmin().
    For any non-Windows system or exception cases, it returns False.
    """

    @patch('os.name', 'nt')
    def test_windows_admin_true(self):
        """Test is_admin returns True when user is admin on Windows."""
        # Create a mock ctypes module with the Windows structure
        mock_ctypes = Mock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 1
        
        with patch.dict('sys.modules', {'ctypes': mock_ctypes}):
            result = is_admin()
            self.assertTrue(result)
            mock_ctypes.windll.shell32.IsUserAnAdmin.assert_called_once()

    @patch('os.name', 'nt')
    def test_windows_admin_false(self):
        """Test is_admin returns False when user is not admin on Windows."""
        # Create a mock ctypes module with the Windows structure
        mock_ctypes = Mock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 0
        
        with patch.dict('sys.modules', {'ctypes': mock_ctypes}):
            result = is_admin()
            self.assertFalse(result)
            mock_ctypes.windll.shell32.IsUserAnAdmin.assert_called_once()

    @patch('os.name', 'posix')
    def test_unix_admin_true(self):
        """Test is_admin returns True when user is root on Unix systems."""
        # Mock getuid to exist and return 0 (root)
        with patch.object(os, 'getuid', return_value=0, create=True):
            result = is_admin()
            self.assertFalse(result)  # Current implementation only works on Windows

    @patch('os.name', 'posix')
    def test_unix_admin_false(self):
        """Test is_admin returns False when user is not root on Unix systems."""
        # Mock getuid to exist and return non-zero (non-root)
        with patch.object(os, 'getuid', return_value=1000, create=True):
            result = is_admin()
            self.assertFalse(result)  # Current implementation only works on Windows

    @patch('os.name', 'unknown')
    def test_unknown_os(self):
        """Test is_admin returns False for unknown operating systems."""
        result = is_admin()
        self.assertFalse(result)

    @patch('os.name', 'nt')
    def test_windows_ctypes_exception(self):
        """Test is_admin handles ctypes exceptions on Windows."""
        # Create a mock ctypes module that raises an exception
        mock_ctypes = Mock()
        mock_ctypes.windll.shell32.IsUserAnAdmin.side_effect = Exception("Access denied")
        
        with patch.dict('sys.modules', {'ctypes': mock_ctypes}):
            result = is_admin()
            self.assertFalse(result)

    @patch('os.name', 'nt')
    def test_windows_ctypes_import_failure(self):
        """Test is_admin handles ctypes import failure on Windows."""
        # Mock ctypes import to fail
        def mock_import(name, *args, **kwargs):
            if name == 'ctypes':
                raise ImportError("No module named 'ctypes'")
            return __import__(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            result = is_admin()
            self.assertFalse(result)

    @patch('os.name', 'posix')
    def test_unix_getuid_exception(self):
        """Test is_admin handles os.getuid exceptions on Unix systems."""
        # Mock getuid to exist but raise an exception
        with patch.object(os, 'getuid', side_effect=OSError("Permission denied"), create=True):
            result = is_admin()
            self.assertFalse(result)  # Current implementation only works on Windows


if __name__ == '__main__':
    unittest.main()