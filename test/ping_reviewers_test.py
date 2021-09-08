#!/usr/bin/env python3
"""Tests for the ping_reviewers script."""

from importlib import machinery
from importlib import util
import os
from os import path
import shutil
import time
import unittest
from unittest import mock

# Dynamic import of script without suffix. See https://stackoverflow.com/a/51575963/4482064
machinery.SOURCE_SUFFIXES.append('')
_SCRIPT_PATH = f'{path.dirname(path.dirname(path.abspath(__file__)))}/bin/ping_reviewers'
_SCRIPT_SPEC = util.spec_from_file_location('ping_reviewers', _SCRIPT_PATH)
ping_reviewers = util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(ping_reviewers)


# TODO(cyrille): Add more tests.
# TODO(cyrille): Use requests_mock.
@mock.patch(ping_reviewers.requests.__name__ + '.get')
class PingReviewersTestCase(unittest.TestCase):
    """Tests for the ping reviewers feature."""

    @mock.patch('logging.info')
    def test_no_slack_url(self, mock_logging: mock.MagicMock, mock_get: mock.MagicMock) -> None:
        """No ping when Slack URL is not present."""

        self.assertFalse(ping_reviewers.main(env={'GITHUB_TOKEN': 'my-github-token'}))
        self.assertFalse(mock_get.called)
        self.assertIn('SLACK_INTEGRATION_URL', [
            word
            for call in mock_logging.call_args_list
            for arguments in call for arg in arguments
            if isinstance(arg, str)
            for word in arg.split(' ')])

    @mock.patch(ping_reviewers.requests.__name__ + '.post')
    def test_directory(self, mock_post: mock.MagicMock, mock_get: mock.MagicMock) -> None:
        """Read all files in a given directory as demos."""

        temp_dir = f'/tmp/whatever_{int(time.time()):d}'
        os.mkdir(temp_dir)
        with open(path.join(temp_dir, 'demo'), 'w') as file:
            file.write('https://demo.example.com')
        with open(path.join(temp_dir, 'other'), 'w') as file:
            file.write('https://other.example.com')
        mock_get().json.return_value = {
            'assignees': [{'login': 'your-user'}],
            'node_id': 'my-node-id',
            'number': 42,
            'title': 'Title',
            'user': {'login': 'my-user'},
        }
        mock_post().json.return_value = \
            {'data': {'node': {'commits': {'nodes': [{'commit': {'statusCheckRollup': {
                'contexts': {'nodes': []},
                'state': 'PENDING',
            }}}]}}}}
        self.assertTrue(ping_reviewers.main(('-d', temp_dir), env={
            'CIRCLE_PROJECT_USERNAME': 'bayesimpact',
            'CIRCLE_PROJECT_REPONAME': 'docker-circleci',
            'CIRCLE_PULL_REQUEST': '/42',
            'CIRCLE_SHA1': 'sha',
            'GITHUB_TOKEN': 'my-token',
            'SLACK_INTEGRATION_URL': 'my_url',
        }), msg=mock_post.call_args_list)
        self.assertEqual(
            mock_get.call_args[0][0],
            'https://api.github.com/repos/bayesimpact/docker-circleci/pulls/42')
        self.assertIn(
            'other.example.com', mock_post.call_args_list[-1].kwargs['json']['text'])
        self.assertIn(
            'demo.example.com', mock_post.call_args_list[-1].kwargs['json']['text'])
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()
