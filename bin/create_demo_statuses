#!/usr/bin/env python3
"""A script to add demo URLs in github statuses.

Assumes a CIRCLE CI context, with the following additional environment:
- GITHUB_TOKEN: a Github token with status access on commits.
It is available in bayesimpact org under the Slack context.
"""

import argparse
import os
from os import path
from typing import Optional, Sequence

import requests

_STATUSES_URL = (
    f'https://api.github.com/repos/{os.getenv("CIRCLE_PROJECT_USERNAME")}/'
    f'{os.getenv("CIRCLE_PROJECT_REPONAME")}/statuses/{os.getenv("CIRCLE_SHA1")}')
_GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
_DEMO_CONTEXT_PREFIX = 'bayesimpact/demo-'


def create_demo_status(name: str, url: str) -> None:
    """Create a Github status for the given demo."""

    response = requests.post(_STATUSES_URL, headers={
        'Accept': 'application/vnd.github.machine-man-preview+json',
        'Authorization': f'token {_GITHUB_TOKEN}',
    }, json={
        'state': 'success',
        'context': f'{_DEMO_CONTEXT_PREFIX}{name}',
        'description': f'{name.capitalize()} demo is ready',
        'target_url': url,
    })
    response.raise_for_status()


def main(string_args: Optional[Sequence[str]] = None) -> None:
    """Parse input arguments, and run the script."""

    if not _GITHUB_TOKEN:
        raise ValueError('Need a Github token, please set GITHUB_TOKEN')
    if 'None' in _STATUSES_URL:
        raise ValueError('This script should be run in a CircleCI environment.')
    parser = argparse.ArgumentParser(description='Add demo URLs in github statuses')
    parser.add_argument('--demo-url', '-u', help='''A demo URL to add.
        Should be given as two arguments: first the name of the demo, then the url itself.
    ''', nargs=2, action='append')
    parser.add_argument('--directory', '-d', help='''
        A folder where files represent different URLs to load.

        Each file should be named with the demo name (e.g. "frontend")
        and contain one line with the demo's URL.
    ''')
    args = parser.parse_args(string_args)
    demo_urls: dict[str, str] = dict(args.demo_url or [])
    if args.directory:
        for filename in os.listdir(args.directory):
            with open(path.join(args.directory, filename)) as file:
                demo_urls[filename] = file.read().strip()
    for name, url in demo_urls.items():
        create_demo_status(name, url)


if __name__ == '__main__':
    main()
