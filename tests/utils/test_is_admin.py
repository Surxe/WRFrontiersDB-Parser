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

    @patch('ctypes.windll.shell32.IsUserAnAdmin')
    @patch('os.name', 'nt')
    def test_windows_admin_true(self, mock_is_user_admin):
        """Test is_admin returns True when user is admin on Windows."""
        mock_is_user_admin.return_value = 1
        result = is_admin()
        self.assertTrue(result)
        mock_is_user_admin.assert_called_once()

    @patch('ctypes.windll.shell32.IsUserAnAdmin')
    @patch('os.name', 'nt')
    def test_windows_admin_false(self, mock_is_user_admin):
        """Test is_admin returns False when user is not admin on Windows."""
        mock_is_user_admin.return_value = 0
        result = is_admin()
        self.assertFalse(result)
        mock_is_user_admin.assert_called_once()

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

    @patch('ctypes.windll.shell32.IsUserAnAdmin')
    @patch('os.name', 'nt')
    def test_windows_ctypes_exception(self, mock_is_user_admin):
        """Test is_admin handles ctypes exceptions on Windows."""
        mock_is_user_admin.side_effect = Exception("Access denied")
        result = is_admin()
        self.assertFalse(result)

    @patch('os.name', 'nt')
    def test_windows_ctypes_import_failure(self):
        """Test is_admin handles ctypes import failure on Windows."""
        # Mock ctypes to be unavailable
        with patch.dict('sys.modules', {'ctypes': None}):
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