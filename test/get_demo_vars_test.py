#!/usr/bin/env python3
"""Tests for the get_demo_vars script."""

import contextlib
from importlib import abc
from importlib import machinery
from importlib import util
import os
from os import path
import shutil
import subprocess
import tempfile
import types
import typing
from typing import Iterator, Optional
import unittest
from unittest import mock

if typing.TYPE_CHECKING:
    class _GetDemoVars(types.ModuleType):
        # pylint: disable=invalid-name
        def main(
                self, string_args: Optional[list[str]],
                env: Optional[dict[str, str]] = None) -> str:
            """Run the get_demo_vars script."""

        requests: types.ModuleType

# Dynamic import of script without suffix. See https://stackoverflow.com/a/51575963/4482064
machinery.SOURCE_SUFFIXES.append('')
_SCRIPT_PATH = f'{path.dirname(path.dirname(path.abspath(__file__)))}/bin/get_demo_vars'
_SCRIPT_SPEC = util.spec_from_file_location('get_demo_vars', _SCRIPT_PATH)
assert _SCRIPT_SPEC
get_demo_vars = typing.cast('_GetDemoVars', util.module_from_spec(_SCRIPT_SPEC))
assert _SCRIPT_SPEC.loader
typing.cast(abc.Loader, _SCRIPT_SPEC.loader).exec_module(get_demo_vars)


def _run_git(*command: str) -> str:
    return subprocess.check_output(
        ['git', '-c', 'user.email=test@example.com', '-c', 'user.name=TEST'] + list(command),
        text=True).strip()


@contextlib.contextmanager
def simple_branch(name: str) -> Iterator[None]:
    """Create a branch with the given name and add a staged file.

    Deletes the branch once the manager is closed.
    """

    _run_git('checkout', '-q', '-b', name)
    with open('somefile', 'w'):
        pass
    _run_git('add', 'somefile')
    try:
        yield None
    finally:
        _run_git('checkout', '-q', '-')
        _run_git('branch', '-D', name)


class DemoVarsTestCase(unittest.TestCase):
    """Tests for the demo vars script."""

    _previous_dir = os.getcwd()
    _dir = tempfile.mkdtemp(dir='/tmp')

    @classmethod
    def setUpClass(cls) -> None:
        os.chdir(cls._dir)
        _run_git('init')
        with open('some_init_file', 'w'):
            pass
        _run_git('add', 'some_init_file')
        _run_git('commit', '-anm', 'First commit.')
        _run_git('branch', '-m', 'main')

    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(cls._previous_dir)
        shutil.rmtree(cls._dir, ignore_errors=True)

    @staticmethod
    def _run_with_branch_and_tag(
            var: Optional[str] = None, *,
            branch: str = '', tag: str = '', env: Optional[dict[str, str]] = None) -> str:
        return get_demo_vars.main([var] if var else None, {
            'CIRCLE_BRANCH': branch,
            'CIRCLE_TAG': tag,
            'CIRCLE_PROJECT_REPONAME': 'bob',
            'CIRCLE_PROJECT_USERNAME': 'bayes',
            'CIRCLE_WORKFLOW_ID': '',
        } | (env or {}))

    def test_default_branch(self) -> None:
        """Returns the expected value on the default branch."""

        default_branch = 'main'
        self.assertEqual('', self._run_with_branch_and_tag(branch=default_branch))

    def test_release_tag(self) -> None:
        """Returns the expected value on a release tag."""

        self.assertEqual('', self._run_with_branch_and_tag(tag='2020-02-18_01'))

    def test_simple_branch(self) -> None:
        """Returns the expected value on a side branch."""

        with simple_branch('cyrille-branch'):
            _run_git('commit', '-nm', 'Simple message.')
            self.assertEqual(
                'repo=bayes%2Fbob&branch=bayes%3Acyrille-branch',
                self._run_with_branch_and_tag(branch='cyrille-branch'))
            self.assertEqual(
                'bayes/bob', self._run_with_branch_and_tag('repo', branch='cyrille-branch'))

    def test_branch_with_path(self) -> None:
        """Returns a path when there's one in the commit message."""

        with simple_branch('cyrille-path'):
            _run_git('commit', '-nm', 'A simple commit.\n\nPATH=/eval')
            self.assertEqual(
                'repo=bayes%2Fbob&branch=bayes%3Acyrille-path&path=%2Feval',
                self._run_with_branch_and_tag(branch='cyrille-path'))

    @mock.patch(get_demo_vars.requests.__name__ + '.get')
    def test_with_demo_waiter(self, mock_get: mock.MagicMock) -> None:
        """Yield a ci_callback_url when there's a wait-for-demo approval in workflow."""

        mock_get.return_value.json.return_value = {'items': [{
            'approval_request_id': 'i-approve-this',
            'name': 'wait-for-demo',
            'type': 'approval',
        }]}
        with simple_branch('cyrille-callback'):
            _run_git('commit', '-nm', 'Any commit message.')
            self.assertEqual(
                'ci_callback_url=https%3A%2F%2Fcircleci.com%2Fapi%2Fv2%2Fworkflow%2Fmy-workflow-id'
                '%2Fapprove%2Fi-approve-this&repo=bayes%2Fbob&branch=bayes%3Acyrille-callback',
                self._run_with_branch_and_tag(branch='cyrille-callback', env={
                    'CIRCLE_WORKFLOW_ID': 'my-workflow-id',
                    'CIRCLE_API_TOKEN': 'my-circle-token',
                }))
            mock_get.assert_called_with(
                'https://circleci.com/api/v2/workflow/my-workflow-id/job',
                headers={'Circle-Token': 'my-circle-token'})

    @mock.patch(get_demo_vars.requests.__name__ + '.get')
    def test_without_demo_waiter(self, mock_get: mock.MagicMock) -> None:
        """Yield a ci_callback_url when there's a wait-for-demo approval in workflow."""

        mock_get.return_value.json.return_value = {'items': [{
            'approval_request_id': 'i-approve-this',
            'name': 'approve-for-release',
            'type': 'approval',
        }]}
        self.assertEqual('', self._run_with_branch_and_tag(tag='release', env={
            'CIRCLE_WORKFLOW_ID': 'my-workflow-id',
            'CIRCLE_API_TOKEN': 'my-circle-token',
        }))
        mock_get.assert_called_with(
            'https://circleci.com/api/v2/workflow/my-workflow-id/job',
            headers={'Circle-Token': 'my-circle-token'})

    def test_without_circle_token(self) -> None:
        """Yield a ci_callback_url when there's a wait-for-demo approval in workflow."""

        self.assertEqual('', self._run_with_branch_and_tag(
            tag='release', env={'CIRCLE_WORKFLOW_ID': 'my-workflow-id'}))


if __name__ == '__main__':
    unittest.main()
