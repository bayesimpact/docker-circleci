#!/usr/bin/env python3
"""Tests for the ping_reviewers script."""

from importlib import machinery
from importlib import util
from os import path
import unittest
from unittest import mock

# Dynamic import of script without suffix. See https://stackoverflow.com/a/51575963/4482064
machinery.SOURCE_SUFFIXES.append('')
_SCRIPT_NAME = path.basename(__file__).removesuffix('_test.py')
_SCRIPT_PATH = f'{path.dirname(path.dirname(path.abspath(__file__)))}/bin/{_SCRIPT_NAME}'
_SCRIPT_SPEC = util.spec_from_file_location('ping_reviewers', _SCRIPT_PATH)
ping_reviewers = util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(ping_reviewers)


# TODO(cyrille): Add more tests.
class PingReviewersTestCase(unittest.TestCase):
    """Tests for the ping reviewers feature."""

    # TODO(cyrille): Use requests_mock.
    @mock.patch('logging.info')
    @mock.patch(ping_reviewers.requests.__name__ + '.get')
    def test_no_slack_url(self, mock_get: mock.MagicMock, mock_logging: mock.MagicMock) -> None:
        """No ping when Slack URL is not present."""

        self.assertFalse(ping_reviewers.main(env={'GITHUB_TOKEN': 'my-github-token'}))
        self.assertFalse(mock_get.called)
        self.assertIn('SLACK_INTEGRATION_URL', [
            word
            for call in mock_logging.call_args_list
            for arguments in call for arg in arguments
            if isinstance(arg, str)
            for word in arg.split(' ')])


if __name__ == '__main__':
    unittest.main()
