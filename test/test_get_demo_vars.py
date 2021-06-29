#!/usr/bin/env python3
"""Tests for the get_demo_vars script."""

import contextlib
import os
from os import path
import shutil
import subprocess
import tempfile
from typing import Any, Optional
import unittest

_SCRIPT = f'{path.dirname(path.dirname(path.abspath(__file__)))}/bin/get_demo_vars'


def _run_git(*command: str, **kwargs: Any) -> str:
    return subprocess.check_output(
        ['git', '-c', 'user.email=test@example.com', '-c', 'user.name=TEST'] + list(command),
        text=True, **kwargs).strip()


@contextlib.contextmanager
def simple_branch(name: str) -> None:
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

    @classmethod
    def setUpClass(cls) -> None:
        cls._previous_dir = os.getcwd()
        cls._dir = tempfile.mkdtemp(dir='/tmp')
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

    def _run_with_branch_and_tag(
            self, var: Optional[str] = None, *, branch: str = '', tag: str = '') -> str:
        command = [_SCRIPT]
        if var:
            command += [var]
        return subprocess.check_output(command, text=True, env=dict(os.environ, **{
            'CIRCLE_BRANCH': branch,
            'CIRCLE_TAG': tag,
            'CIRCLE_PROJECT_REPONAME': 'bob',
            'CIRCLE_PROJECT_USERNAME': 'bayes',
        })).strip()

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


if __name__ == '__main__':
    unittest.main()
