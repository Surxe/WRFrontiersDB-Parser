"""
Tests for ensure_parser_tree_clean: a push from a parser checkout with
uncommitted changes is refused unless ALLOW_DIRTY_PUSH is set.
"""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

from push.push import ensure_parser_tree_clean


def git_status_result(stdout):
    return SimpleNamespace(stdout=stdout)


class TestEnsureParserTreeClean(unittest.TestCase):

    @patch('push.push.OPTIONS', SimpleNamespace(allow_dirty_push=False))
    @patch('push.push.run_git_command', return_value=git_status_result(""))
    def test_clean_tree_passes(self, mock_git):
        ensure_parser_tree_clean()
        self.assertEqual(mock_git.call_args.args[0], ['git', 'status', '--porcelain'])

    @patch('push.push.OPTIONS', SimpleNamespace(allow_dirty_push=False))
    @patch('push.push.run_git_command', return_value=git_status_result(" M src/push/push.py\n"))
    def test_dirty_tree_raises(self, mock_git):
        with self.assertRaises(RuntimeError) as ctx:
            ensure_parser_tree_clean()
        self.assertIn("src/push/push.py", str(ctx.exception))
        self.assertIn("ALLOW_DIRTY_PUSH", str(ctx.exception))

    @patch('push.push.OPTIONS', SimpleNamespace(allow_dirty_push=False))
    @patch('push.push.run_git_command', return_value=git_status_result("?? src/parse/new_object.py\n"))
    def test_untracked_file_counts_as_dirty(self, mock_git):
        with self.assertRaises(RuntimeError):
            ensure_parser_tree_clean()

    @patch('push.push.OPTIONS', SimpleNamespace(allow_dirty_push=True))
    @patch('push.push.run_git_command', return_value=git_status_result(" M src/push/push.py\n"))
    def test_dirty_tree_allowed_with_override(self, mock_git):
        ensure_parser_tree_clean()

    def test_checks_the_parser_repo_itself(self):
        """The real call runs against this repo, not whatever the cwd is."""
        with patch('push.push.run_git_command', return_value=git_status_result("")) as mock_git:
            ensure_parser_tree_clean()
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.assertEqual(os.path.abspath(mock_git.call_args.kwargs['cwd']), repo_root)


if __name__ == '__main__':
    unittest.main()
