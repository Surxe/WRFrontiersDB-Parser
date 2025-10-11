"""
Simple integration tests for the push module to validate basic functionality.
"""
import unittest
import sys
import os
import tempfile
import json
from pathlib import Path

# Add the src directory to the Python path to import push module
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.push module
import importlib.util
spec = importlib.util.spec_from_file_location("push_module", os.path.join(src_path, "push", "push.py"))
push_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(push_module)


class TestPushModuleFunctions(unittest.TestCase):
    """Test basic functionality of push module functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_remove_readonly_function_exists(self):
        """Test that remove_readonly function exists and is callable."""
        self.assertTrue(hasattr(push_module, 'remove_readonly'))
        self.assertTrue(callable(push_module.remove_readonly))

    def test_run_git_command_function_exists(self):
        """Test that run_git_command function exists and is callable."""
        self.assertTrue(hasattr(push_module, 'run_git_command'))
        self.assertTrue(callable(push_module.run_git_command))

    def test_get_current_version_function_exists(self):
        """Test that get_current_version function exists and is callable."""
        self.assertTrue(hasattr(push_module, 'get_current_version'))
        self.assertTrue(callable(push_module.get_current_version))

    def test_get_current_version_with_file(self):
        """Test get_current_version with a real version.txt file."""
        # Create the directory structure expected by the function
        current_dir = os.path.join(self.temp_dir, "current")
        os.makedirs(current_dir, exist_ok=True)
        
        # Create a test version.txt file
        version_file = os.path.join(current_dir, "version.txt")
        test_version = "1.2.3"
        
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(test_version)
        
        # Test the function
        result = push_module.get_current_version(self.temp_dir)
        self.assertEqual(result, "1.2.3")

    def test_get_current_version_missing_file(self):
        """Test get_current_version with missing version.txt file."""
        result = push_module.get_current_version(self.temp_dir)
        self.assertIsNone(result)

    def test_get_current_version_whitespace_handling(self):
        """Test get_current_version with whitespace in version.txt."""
        # Create the directory structure expected by the function
        current_dir = os.path.join(self.temp_dir, "current")
        os.makedirs(current_dir, exist_ok=True)
        
        version_file = os.path.join(current_dir, "version.txt")
        
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write("  1.2.3  \n")  # Version with whitespace
        
        result = push_module.get_current_version(self.temp_dir)
        self.assertEqual(result, "1.2.3")  # Should be stripped

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        self.assertTrue(hasattr(push_module, 'main'))
        self.assertTrue(callable(push_module.main))

    def test_all_required_functions_exist(self):
        """Test that all required functions exist in the module."""
        required_functions = [
            'remove_readonly',
            'run_git_command', 
            'clone_data_repo',
            'configure_git_repo',
            'switch_to_target_branch',
            'get_latest_commit_info',
            'get_current_version',
            'update_current_data',
            'archive_old_data',
            'push_changes',
            'main'
        ]
        
        for func_name in required_functions:
            with self.subTest(function=func_name):
                self.assertTrue(hasattr(push_module, func_name), f"Missing function: {func_name}")
                self.assertTrue(callable(getattr(push_module, func_name)), f"Function not callable: {func_name}")

    def test_string_command_handling(self):
        """Test that string commands are properly converted to lists."""
        # This is a simple test that doesn't actually run git commands
        # We just verify the function doesn't crash with string input
        try:
            # This will likely fail because git isn't set up, but we're just testing
            # that the function can handle string input without crashing
            push_module.run_git_command("status", cwd=self.temp_dir)
        except Exception as e:
            # We expect this to fail, but not with a TypeError about string handling
            self.assertNotIsInstance(e, TypeError)
            # Most likely to be CalledProcessError or similar git-related error


if __name__ == '__main__':
    unittest.main()