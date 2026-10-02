"""
The data repo PAT must reach git through the environment only, never the remote URL
(which git writes to .git/config, leaving the PAT on disk between runs).
"""
import base64
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

from push.push import (
    DATA_REPO_URL, configure_git_repo, git_auth_env, redact_secrets, run_git_command,
)

FAKE_PAT = 'github_pat_FAKE0000000000000000'
FAKE_OPTIONS = SimpleNamespace(
    gh_data_repo_pat=FAKE_PAT,
    schema={'GH_DATA_REPO_PAT': {'var': 'gh_data_repo_pat', 'sensitive': True}},
)


@patch('push.push.OPTIONS', FAKE_OPTIONS)
class TestGitAuthEnv(unittest.TestCase):

    def test_git_auth_env_sets_extraheader(self):
        env = git_auth_env()
        self.assertEqual(env['GIT_CONFIG_COUNT'], '1')
        self.assertEqual(env['GIT_CONFIG_KEY_0'], 'http.https://github.com/.extraheader')
        encoded = env['GIT_CONFIG_VALUE_0'].removeprefix('AUTHORIZATION: basic ')
        self.assertEqual(base64.b64decode(encoded).decode(), f'x-access-token:{FAKE_PAT}')

    def test_git_auth_env_empty_without_pat(self):
        with patch('push.push.OPTIONS', SimpleNamespace(gh_data_repo_pat=None, schema={})):
            self.assertEqual(git_auth_env(), {})

    @patch('push.push.subprocess.run')
    def test_run_git_command_passes_auth_env(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='')
        run_git_command(['git', 'status'])
        env = mock_run.call_args[1]['env']
        self.assertEqual(env['GIT_CONFIG_KEY_0'], 'http.https://github.com/.extraheader')

    @patch('push.push.run_git_command')
    def test_configure_git_repo_sets_plain_remote_url(self, mock_git_command):
        configure_git_repo('/tmp/repo')
        set_url = [c[0][0] for c in mock_git_command.call_args_list if c[0][0][1:3] == ['remote', 'set-url']]
        self.assertEqual(set_url, [['git', 'remote', 'set-url', 'origin', DATA_REPO_URL]])
        for c in mock_git_command.call_args_list:
            self.assertNotIn(FAKE_PAT, ' '.join(c[0][0]))

    def test_redact_secrets_masks_encoded_pat(self):
        header = git_auth_env()['GIT_CONFIG_VALUE_0']
        self.assertNotIn(FAKE_PAT, redact_secrets(f'pat={FAKE_PAT}'))
        self.assertEqual(redact_secrets(header), 'AUTHORIZATION: basic ********')

    def test_real_git_reads_auth_env_without_writing_config(self):
        """Against real git: the env config is visible to git, and .git/config stays clean."""
        with tempfile.TemporaryDirectory() as repo_dir:
            subprocess.run(['git', 'init', '-q', repo_dir], check=True)
            run_git_command(['git', 'remote', 'add', 'origin', DATA_REPO_URL], cwd=repo_dir)
            result = run_git_command(
                ['git', 'config', '--get', 'http.https://github.com/.extraheader'], cwd=repo_dir
            )
            self.assertTrue(result.stdout.startswith('AUTHORIZATION: basic '))
            with open(os.path.join(repo_dir, '.git', 'config'), encoding='utf-8') as f:
                config = f.read()
            self.assertNotIn(FAKE_PAT, config)
            self.assertNotIn('extraheader', config)


if __name__ == '__main__':
    unittest.main(verbosity=2)
