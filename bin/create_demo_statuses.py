#!/usr/bin/env python3
"""A script to add demo URLs in github statuses.

Assumes a CIRCLE CI context, with the following additional environment:
- GITHUB_TOKEN: a Github token with status access on commits.
It is available in bayesimpact org under the Slack context.
"""

import argparse
import logging
import os
from os import path
import time
import typing
from typing import Optional, Sequence, Set
from urllib import parse

import requests

if typing.TYPE_CHECKING:
    import create_demo_statuses_types as types

_STATUSES_URL = (
    f'https://api.github.com/repos/{os.getenv("CIRCLE_PROJECT_USERNAME")}/'
    f'{os.getenv("CIRCLE_PROJECT_REPONAME")}/statuses/{os.getenv("CIRCLE_SHA1")}')
_GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
_DEMO_CONTEXT_PREFIX = 'bayesimpact/demo-'

_DEPLOYMENTS_GRAPHQL_QUERY = '''query($repo: String!, $owner: String!, $prNumber: Int!) {
  repository(name: $repo, owner: $owner) {
    pullRequest(number: $prNumber) {
      commits(last: 1) {
        nodes {
          commit {
            messageBody
          }
        }
      }
      timelineItems(last: 10, itemTypes: [DEPLOYED_EVENT]) {
        nodes {
          ...on DeployedEvent {
            deployment {
              description
              state
              latestStatus {
                environmentUrl
              }
            }
          }
        }
      }
    }
  }
}'''


_USELESS_DEPLOYMENT_STATES: Set['types._DeploymentState'] = {
    'INACTIVE',
}
_READY_DEPLOYMENT_STATES: Set['types._DeploymentState'] = {
    'ACTIVE',
}
_FAILED_DEPLOYMENT_STATES: Set['types._DeploymentState'] = {
    'ABANDONED',
    'DESTROYED',
    'ERROR',
    'FAILURE',
}
_WAITING_DEPLOYMENT_STATES: Set['types._DeploymentState'] = {
    'PENDING',
    'QUEUED',
    'IN_PROGRESS',
    'WAITING',
}


def create_demo_status(name: str, url: Optional[str]) -> None:
    """Create a Github status for the given demo."""

    state = 'success' if url else 'failure'
    response = requests.post(_STATUSES_URL, headers={
        'Accept': 'application/vnd.github.machine-man-preview+json',
        'Authorization': f'token {_GITHUB_TOKEN}',
    }, json={
        'state': state,
        'context': f'{_DEMO_CONTEXT_PREFIX}{name}',
        'description': f'{name.capitalize()} demo is ready',
    } | ({'target_url': url} if url else {}))
    response.raise_for_status()


def wait_for_deployment_urls(
        deployments: Set[str], max_retry: int = 10) -> dict[str, Optional[str]]:
    if not deployments:
        return {}
    deployments = set(deployments)
    owner = os.getenv('CIRCLE_PROJECT_USERNAME')
    try:
        pr_number = int(os.getenv('CIRCLE_PULL_REQUEST', '').rsplit('/', 1)[-1])
    except ValueError as error:
        raise ValueError('Missing a pull request for which to check deployments.') from error
    repo = os.getenv('CIRCLE_PROJECT_REPONAME')
    token = os.getenv('GITHUB_TOKEN')
    if not owner or not repo or not token:
        return {}
    result: dict[str, Optional[str]] = {}
    for unused_ in range(max_retry):
        response = requests.post('https://api.github.com/graphql', json={
            'query': _DEPLOYMENTS_GRAPHQL_QUERY,
            'variables': {
                'owner': owner,
                'prNumber': pr_number,
                'repo': repo,
            },
        }, headers={'Authorization': f'token {token}'})
        response.raise_for_status()
        response_data: 'types._Response' = response.json()
        pull_request = response_data.get('data', {}).get('repository', {}).get('pullRequest', {})
        url_path = next((
            line.removeprefix('PATH=')
            for pr_commit in pull_request.get('commits', {}).get('nodes', [])
            for line in pr_commit.get('commit', {}).get('messageBody', '').split('\n')
            if line.startswith('PATH=')), None)
        for event in pull_request.get('timelineItems', {}).get('nodes', []):
            deployment = event.get('deployment', {})
            name = deployment.get('description', '').lower()
            if name not in deployments:
                continue
            state = deployment.get('state')
            if not state or state in _USELESS_DEPLOYMENT_STATES:
                continue
            if state in _FAILED_DEPLOYMENT_STATES:
                result[name] = None
            if state in _WAITING_DEPLOYMENT_STATES:
                break
            if state not in _READY_DEPLOYMENT_STATES:
                continue
            url = deployment.get('latestStatus', {}).get('environmentUrl')
            if not url:
                raise ValueError('Got a ready deployment without a URL...')
            result[name] = parse.urljoin(url, url_path or '')
        else:
            deployments -= set(result)
            if not deployments:
                return result
        time.sleep(2)
    logging.warning('Could not find deployment URLs for "%s"', '", "'.join(deployments))
    return result


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
    parser.add_argument('--deployment', dest='deployments', action='append', help='''
        Wait for GitHub deployment(s) to be ready, and link their URL''')
    args = parser.parse_args(string_args)
    demo_urls: dict[str, Optional[str]] = dict(args.demo_url or [])
    if args.directory:
        for filename in os.listdir(args.directory):
            with open(path.join(args.directory, filename)) as file:
                demo_urls[filename] = file.read().strip()
    demo_urls |= wait_for_deployment_urls({d.lower() for d in args.deployments or []})
    for name, url in demo_urls.items():
        create_demo_status(name, url)


if __name__ == '__main__':
    main()
