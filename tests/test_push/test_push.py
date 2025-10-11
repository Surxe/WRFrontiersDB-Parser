"""
Fixed mock tests for the push module using proper patching techniques.
"""
import unittest
import sys
import os
import tempfile
import shutil
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Add the src directory to the Python path to import push module
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import the push module using proper import
try:
    from push.push import (
        remove_readonly, run_git_command, clone_data_repo, configure_git_repo,
        switch_to_target_branch, get_latest_commit_info, get_current_version,
        update_current_data, archive_old_data, push_changes, main
    )
except ImportError:
    # Fallback to dynamic loading if direct import fails
    import importlib.util
    spec = importlib.util.spec_from_file_location("push_module", os.path.join(src_path, "push", "push.py"))
    push_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(push_module)
    
    # Extract functions from the dynamically loaded module
    remove_readonly = push_module.remove_readonly
    run_git_command = push_module.run_git_command
    clone_data_repo = push_module.clone_data_repo
    configure_git_repo = push_module.configure_git_repo
    switch_to_target_branch = push_module.switch_to_target_branch
    get_latest_commit_info = push_module.get_latest_commit_info
    get_current_version = push_module.get_current_version
    update_current_data = push_module.update_current_data
    archive_old_data = push_module.archive_old_data
    push_changes = push_module.push_changes
    main = push_module.main


class TestRunGitCommand(unittest.TestCase):
    """Test cases for the run_git_command function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('push.push.subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_run.return_value = mock_result
        
        result = run_git_command(['git', 'status'], cwd=self.temp_dir)
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        
        # Check positional arguments
        self.assertEqual(call_args[0][0], ['git', 'status'])
        
        # Check keyword arguments
        self.assertEqual(call_args[1]['cwd'], self.temp_dir)
        self.assertEqual(call_args[1]['encoding'], 'utf-8')
        self.assertEqual(call_args[1]['errors'], 'ignore')
        self.assertTrue(call_args[1]['text'])
        self.assertTrue(call_args[1]['capture_output'])
        
        # The function returns the CompletedProcess object, not just stdout
        self.assertEqual(result, mock_result)

    @patch('push.push.subprocess.run')
    def test_run_git_command_string_input(self, mock_run):
        """Test git command with string input (should be converted to list)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_run.return_value = mock_result
        
        result = run_git_command('git status', cwd=self.temp_dir)
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        
        # Should convert string to list
        self.assertEqual(call_args[0][0], ['git', 'status'])
        self.assertEqual(result, mock_result)

    @patch('push.push.subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command failure handling."""
        error = subprocess.CalledProcessError(1, ['git', 'status'])
        error.stderr = "error message"
        error.stdout = "some error output"
        mock_run.side_effect = error
        
        with self.assertRaises(subprocess.CalledProcessError):
            run_git_command(['git', 'status'], cwd=self.temp_dir)

    @patch('push.push.os.environ')
    @patch('push.push.subprocess.run')
    def test_run_git_command_env_variables(self, mock_run, mock_environ):
        """Test git command with environment variables."""
        mock_environ.copy.return_value = {'PATH': '/usr/bin', 'HOME': '/home/user'}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_run.return_value = mock_result
        
        # The function doesn't accept env_vars parameter, it sets up its own environment
        run_git_command(['git', 'status'], cwd=self.temp_dir)
        
        # Check that proper environment variables were set
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        env = call_args[1]['env']
        
        # Should have the default git config override variables
        self.assertIn('GIT_CONFIG_NOSYSTEM', env)
        self.assertEqual(env['GIT_CONFIG_NOSYSTEM'], '1')


class TestRemoveReadonly(unittest.TestCase):
    """Test cases for remove_readonly function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('push.push.os.chmod')
    @patch('push.push.stat')
    def test_remove_readonly(self, mock_stat, mock_chmod):
        """Test remove_readonly function."""
        test_path = os.path.join(self.temp_dir, "test_file.txt")
        
        # Mock the stat module constants
        mock_stat.S_IWRITE = 0o200
        
        # Create a mock function to pass as the first parameter
        mock_func = MagicMock()
        
        remove_readonly(mock_func, test_path, None)
        
        # Should call chmod to remove readonly
        mock_chmod.assert_called_once_with(test_path, mock_stat.S_IWRITE)
        # Should then call the provided function
        mock_func.assert_called_once_with(test_path)


class TestCloneDataRepo(unittest.TestCase):
    """Test cases for clone_data_repo function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('push.push.shutil.rmtree')
    @patch('push.push.os.path.exists')
    @patch('push.push.run_git_command')
    def test_clone_data_repo_new_dir(self, mock_git_command, mock_exists, mock_rmtree):
        """Test cloning to a new directory."""
        mock_exists.return_value = False
        
        clone_data_repo(self.temp_dir, "fake_token")
        
        # Should not attempt to remove directory if it doesn't exist
        mock_rmtree.assert_not_called()
        
        # Should call git clone
        mock_git_command.assert_called_once()
        call_args = mock_git_command.call_args[0][0]
        self.assertTrue(call_args[0] == 'git' or call_args == ['git'])

    @patch('push.push.shutil.rmtree')
    @patch('push.push.os.path.exists')
    @patch('push.push.run_git_command')
    def test_clone_data_repo_existing_dir(self, mock_git_command, mock_exists, mock_rmtree):
        """Test cloning when directory already exists."""
        mock_exists.return_value = True
        
        clone_data_repo(self.temp_dir, "fake_token")
        
        # Should remove existing directory
        mock_rmtree.assert_called_once()
        
        # Should call git clone
        mock_git_command.assert_called_once()


class TestGetCurrentVersion(unittest.TestCase):
    """Test cases for get_current_version function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_current_version_exists(self):
        """Test get_current_version with existing version file."""
        # Create current directory and version file
        current_dir = os.path.join(self.temp_dir, "current")
        os.makedirs(current_dir)
        version_file = os.path.join(current_dir, "version.txt")
        
        with open(version_file, 'w') as f:
            f.write("1.2.3\n")
        
        result = get_current_version(self.temp_dir)
        self.assertEqual(result, "1.2.3")

    def test_get_current_version_not_exists(self):
        """Test get_current_version with missing version file."""
        result = get_current_version(self.temp_dir)
        self.assertIsNone(result)


class TestConfigureGitRepo(unittest.TestCase):
    """Test cases for configure_git_repo function."""

    @patch('push.push.run_git_command')
    def test_configure_git_repo(self, mock_git_command):
        """Test git repository configuration."""
        test_dir = "/fake/path"
        
        configure_git_repo(test_dir)
        
        # Should call git config commands
        self.assertEqual(mock_git_command.call_count, 3)
        
        # Check the calls
        calls = mock_git_command.call_args_list
        
        # Check email config
        self.assertIn('user.email', ' '.join(calls[0][0][0]))
        
        # Check name config  
        self.assertIn('user.name', ' '.join(calls[1][0][0]))
        
        # Check credential helper config
        self.assertIn('credential.helper', ' '.join(calls[2][0][0]))


class TestMainFunction(unittest.TestCase):
    """Test cases for main function."""

    def test_main_missing_token(self):
        """Test main function with missing GitHub token."""
        # Import the module to access it
        try:
            import push.push as push_module
        except ImportError:
            # Fallback - skip these tests since they require complex setup
            self.skipTest("Cannot import push.push module for testing")
            
        with patch.object(push_module, 'init_options') as mock_init_options:
            mock_opts = MagicMock()
            mock_opts.gh_data_repo_pat = None
            mock_opts.game_version = "1.0.0"  # Valid game version
            mock_init_options.return_value = mock_opts
            
            # Set the OPTIONS global variable directly
            push_module.OPTIONS = mock_opts
            
            with self.assertRaises(ValueError) as context:
                main(mock_opts)
            
            self.assertIn("GH_DATA_REPO_PAT", str(context.exception))

    def test_main_missing_game_version(self):
        """Test main function with missing game version."""
        # Import the module to access it
        try:
            import push.push as push_module
        except ImportError:
            # Fallback - skip these tests since they require complex setup
            self.skipTest("Cannot import push.push module for testing")
            
        with patch.object(push_module, 'init_options') as mock_init_options:
            mock_opts = MagicMock()
            mock_opts.gh_data_repo_pat = "fake_token"
            mock_opts.game_version = None
            mock_init_options.return_value = mock_opts
            
            # Set the OPTIONS global variable directly
            push_module.OPTIONS = mock_opts
            
            with self.assertRaises(ValueError) as context:
                main(mock_opts)
            
            self.assertIn("GAME_VERSION", str(context.exception))


if __name__ == '__main__':
    # Register a custom test loader that skips tests if imports fail
    unittest.main(verbosity=2)