#!/usr/bin/env python3
"""Tests for the ping_reviewers script."""

from importlib import machinery
from importlib import util
from os import path
import unittest
from unittest import mock

# Dynamic import of script without suffix. See https://stackoverflow.com/a/51575963/4482064
machinery.SOURCE_SUFFIXES.append('')
_SCRIPT_PATH = f'{path.dirname(path.dirname(path.abspath(__file__)))}/bin/ping_reviewers'
_SCRIPT_SPEC = util.spec_from_file_location('ping_reviewers', _SCRIPT_PATH)
ping_reviewers = util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(ping_reviewers)


# TODO(cyrille): Add more tests.
class PingReviewersTestCase(unittest.TestCase):
    """Tests for the ping reviewers feature."""

    @mock.patch('logging.info')
    def test_no_slack_url(self, mock_logging: mock.MagicMock) -> None:
        """No ping when Slack URL is not present."""

        self.assertFalse(ping_reviewers.main(env={'GITHUB_TOKEN': 'my-github-token'}))
        self.assertIn('SLACK_INTEGRATION_URL', [
            word
            for call in mock_logging.call_args_list
            for arguments in call for arg in arguments
            if isinstance(arg, str)
            for word in arg.split(' ')])


if __name__ == '__main__':
    unittest.main()
