#!/usr/bin/env python3
"""
Check TODOs that have been added or deleted for a given duration on the repo.
Run using check_recent_todos duration [folder]
      duration is a `git log`-readable duration, e.g. '7 days' (default)
      folder is a subfolder of the current repo in which we look for the TODOs.
"""

import argparse
import functools
import logging
import os
from os import path
import re
import subprocess
import sys
import typing
from typing import Any, Dict, Iterator, List, Optional

import requests


def _run_git(git_command: List[str]) -> str:
    return subprocess.check_output(['git'] + git_command, text=True).strip()


def _grep_all_todos(folder: str) -> List[str]:
    return subprocess.check_output(['grep', r'\bTODO\b', '-nrI', folder], text=True).split('\n')


_TODO_FILE_REGEX = re.compile(r'^([^:]*):')
_TODO_LINE_REGEX = re.compile(r'\bTODO\b(?:\(([^)]+)\))?:?\s*(.*)')

_SLACK_INTEGRATION_URL = os.getenv('SLACK_INTEGRATION_URL')
_PROJECT_USERNAME = os.getenv('CIRCLE_PROJECT_USERNAME', 'bayesimpact')
_PROJECT_REPONAME = os.getenv('CIRCLE_PROJECT_REPONAME', 'bob-emploi-internal')
_GIT_SHA1 = os.getenv('CIRCLE_SHA1') or _run_git(['rev-parse', 'HEAD'])
_IS_TTY = sys.stdout.isatty()
_URL_TO_FILE = f'https://github.com/{_PROJECT_USERNAME}/{_PROJECT_REPONAME}/blob/{_GIT_SHA1}/'


@functools.lru_cache
def _get_repo_root() -> str:
    return _run_git(['rev-parse', '--show-toplevel'])


class _TodoRef(typing.NamedTuple):
    file: str
    line: int
    text: str
    owner: Optional[str] = None

    @staticmethod
    def parse_line(todo_line: str) -> Optional['_TodoRef']:
        """Parse a line from grep result to a _TodoRef."""

        if not todo_line:
            return None
        try:
            file, line_str, full_text = todo_line.split(':', 2)
        except ValueError:
            logging.error('Unable to split line:\n%r', todo_line)
            return None
        owner: Optional[str] = None
        text = full_text
        match = _TODO_LINE_REGEX.search(full_text)
        if match:
            owner, text = match.groups()
        return _TodoRef(file, int(line_str), text, owner)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, _TodoRef):
            return False
        return self.file == other.file and self.text == other.text

    def __str__(self) -> str:
        owner_text = f'{self.owner}: ' if self.owner else ''
        return f'{self.file}#L{self.line}: {owner_text}{self.text}'

    def format_for_tty(self) -> str:
        """Format the _TodoRef with colors if it's in a terminal."""

        if not _IS_TTY:
            return str(self)

        owner_text = f'{self.owner}: ' if self.owner else ''
        return (
            f'{self.file}\x1b[38;5;243m#\x1b[mL{self.line}\x1b[m: '
            f'\x1b[38;5;38m{owner_text}\x1b[38;5;2m{self.text}\x1b[m'
        )

    def format_for_slack(self) -> str:
        """Format the _TodoRef for slack output."""

        owner_text = f'{self.owner}: ' if self.owner else ''
        return f'<{_URL_TO_FILE}{path.relpath(self.file, start=_get_repo_root())}#L{self.line}' + \
            f'|{self.file}:{self.line}>: {owner_text}{self.text}'


def _grep_and_parse_all_todos(folder: str) -> Iterator[_TodoRef]:
    useless_folder_prefix = './'
    for todo_line in _grep_all_todos(folder):
        if todo_line.startswith(useless_folder_prefix):
            todo_line = todo_line[len(useless_folder_prefix):]
        if not todo_line.strip():
            continue
        if line := _TodoRef.parse_line(todo_line):
            yield line


def _make_message(new_todos: List[_TodoRef], closed_todos_count: int) -> str:
    """Create a message that will be shown about the TODO diff."""

    message_lines: List[str] = []
    if closed_todos_count or new_todos:
        message_lines.extend([
            f'Removed {closed_todos_count} TODOs',
            f'Added {len(new_todos)} TODOs:'])
    else:
        message_lines.append('No changes in TODOs.')
    return '\n'.join(message_lines + [todo.format_for_tty() for todo in new_todos])


def _make_slack_message(new_todos: List[_TodoRef], closed_todos_count: int, duration: str) \
        -> Dict[str, str]:
    """Create a message that will be sent to slack about the TODO diff."""

    todos_added = '\n'.join(todo.format_for_slack() for todo in new_todos)
    return {
        'text': f'{_PROJECT_USERNAME}/{_PROJECT_REPONAME} TODOs modifications since {duration}.\n'
        f'{closed_todos_count} TODOs removed\n{len(new_todos)} TODOs added:\n' + todos_added,
    }


def main(string_args: Optional[List[str]] = None) -> None:
    """Compare previous TODOs from current branch's."""

    parser = argparse.ArgumentParser(
        description='Check TODOs that have been added or deleted for a given duration on the repo.')
    parser.add_argument(
        'duration', default='7 days', nargs='?',
        help="A `git log`-readable duration, e.g. '7 days' (default).")
    parser.add_argument(
        'folder', default='.', nargs='?',
        help='A subfolder of the current repo in which we look for the TODOs.')
    args = parser.parse_args(string_args)

    last_checked_commit = _run_git([
        'log', '--before', args.duration, '--format=%h', '-1', args.folder])
    recent_todos = list(_grep_and_parse_all_todos(args.folder))
    _run_git(['-c', 'advice.detachedHead=false', 'checkout', last_checked_commit])
    old_todos = list(_grep_and_parse_all_todos(args.folder))
    _run_git(['checkout', '-'])
    new_todos = [todo for todo in recent_todos if todo not in old_todos]
    closed_todos_count = sum(1 for todo in old_todos if todo not in recent_todos)
    message = _make_message(new_todos, closed_todos_count)
    print(message)
    if _SLACK_INTEGRATION_URL:
        requests.post(
            _SLACK_INTEGRATION_URL,
            json=_make_slack_message(new_todos, closed_todos_count, args.duration))


if __name__ == '__main__':
    main()
