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
        switch_to_target_branch, get_latest_commit_info,
        update_current_data, push_changes, main
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
    update_current_data = push_module.update_current_data
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


class TestUpdateCurrentDataCommit(unittest.TestCase):
    """The Data commit records the parser commit, as text and as a hash trailer."""

    def setUp(self):
        self.repo_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        Path(self.output_dir, 'Objects.json').write_text('{}')

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _commit_args(self, **kwargs):
        with patch('push.push.run_git_command') as mock_git_command:
            update_current_data(self.repo_dir, self.output_dir, '2026-10-06', 'Fix X (#1) - 2026-10-07', 'main', **kwargs)
        return next(c.args[0] for c in mock_git_command.call_args_list if c.args[0][1] == 'commit')

    def test_sha_trailer(self):
        self.assertEqual(self._commit_args(latest_commit_sha='abc123'), [
            'git', 'commit',
            '-m', "Update current to version '2026-10-06'",
            '-m', "Parser commit: 'Fix X (#1) - 2026-10-07'",
            '-m', 'Parser-Commit: abc123',
        ])

    def test_no_sha_no_trailer(self):
        self.assertNotIn('Parser-Commit', ' '.join(self._commit_args()))


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
        
        clone_data_repo("https://github.com/fake/repo.git", self.temp_dir)
        
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
        
        clone_data_repo("https://github.com/fake/repo.git", self.temp_dir)
        
        # Should remove existing directory
        mock_rmtree.assert_called_once()
        
        # Should call git clone
        mock_git_command.assert_called_once()

if __name__ == '__main__':
    # Register a custom test loader that skips tests if imports fail
    unittest.main(verbosity=2)