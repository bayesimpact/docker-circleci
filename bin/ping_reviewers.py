#!/usr/bin/env python3
"""Ping reviewers for a given branch.

Assumes a CIRCLE CI context, with the following additional environment:
- SLACK_INTEGRATION_URL: a slack webhook URL
- GITHUB_TOKEN: a Github token with read access on Pull Requests
- SLACK_GITHUB_USER_PAIRINGS: a JSON representation of a dict with Github user handles as keys
    and corresponding Slack user IDs as values.
Those are available in bayesimpact org under the Slack context.
"""

import argparse
import datetime
import json
import logging
import os
from os import path
import typing
from typing import Any, Literal, Generic, NamedTuple, Optional, Protocol, Sequence, TypedDict

import requests


class _Config(NamedTuple):
    # The commit sha1.
    commit: str

    # The full name of the changed github repository. Fetched from CircleCI environment.
    github_repo: str

    # A pairing between github user logins and Slack user IDs.
    # Fetched from CircleCI 'Slack' context.
    github_to_slack: dict[str, str]

    # A token to access Github API with read rights on PR info.
    # Fetched from CircleCI 'Slack' context.
    github_token: str

    # The number of the current PR. Fetched from CircleCI environment
    pr_number: str

    # A webhook URL for slack. Fetched from CircleCI 'Slack' context.
    slack_url: str

    # The tag that is currently under CI.
    tag: str

    @staticmethod
    def from_env(environ: Optional[dict[str, str]] = None) -> '_Config':
        """Generate from an environment dict."""

        env = environ or dict(os.environ)
        slack_url = env.get('SLACK_INTEGRATION_URL', '')
        github_token = env.get('GITHUB_TOKEN', '')

        github_repo = '/'.join((
            env.get('CIRCLE_PROJECT_USERNAME', ''), env.get('CIRCLE_PROJECT_REPONAME', '')))
        pr_number = env.get('CIRCLE_PULL_REQUEST', '').rsplit('/', 1)[-1]
        commit_sha = env.get('CIRCLE_SHA1', '')

        github_to_slack: dict[str, str] = json.loads(env.get('SLACK_GITHUB_USER_PAIRINGS', r'{}'))

        tag = env.get('CIRCLE_TAG', '')
        return _Config(
            commit_sha, github_repo, github_to_slack, github_token, pr_number, slack_url, tag)


class _ReviewInfo(NamedTuple):
    """Relevant information aggregated about a PR."""

    # Whether the PR actually needs to be reviewed.
    should_review: bool

    # A URL where a demo can be found for review, if available.
    demo_url: Optional[str] = None


class _GithubUser(TypedDict):
    """A user object."""

    login: str


class _GithubRepo(TypedDict):
    """A repository object."""

    default_branch: str
    full_name: str
    owner: _GithubUser


class _GithubPullRequestBase(TypedDict, total=False):
    """The base commit of a Pull Request."""

    repo: _GithubRepo


class _GithubCommit(TypedDict):
    """A commit objet."""

    message: str
    ref: str
    sha: str


class _GithubPullRequest(TypedDict, total=False):
    """A pull-request object."""

    base: _GithubPullRequestBase
    created_at: str
    node_id: str
    head: _GithubCommit
    number: int
    requested_reviewers: list[_GithubUser]
    assignees: list[_GithubUser]
    user: _GithubUser
    title: str


_T = typing.TypeVar('_T')


class _Connection(Protocol, Generic[_T]):
    def __getitem__(self, nodes: Literal['nodes']) -> list[_T]:
        pass

    def get(self, nodes: Literal['nodes'], default: list[_T]) -> list[_T]:
        pass


# GraphQL query for information about a Pull Request.
# Relevant information:
#   - on the last commit of the PR:
#       - global status state
#       - demo URL from the bayesimpact/demo-frontend status
# See https://docs.github.com/en/graphql for the full reference.
_PULL_REQUEST_INFO_GRAPHQL_QUERY = '''query($prNodeId: ID!) {
    node(id: $prNodeId) {
        ... on PullRequest {
            # Take the last commit.
            commits(last:1) {
                nodes {
                    commit {
                        # Look at its status checks.
                        statusCheckRollup {
                            contexts(last:100) {
                                nodes {
                                    ... on StatusContext {
                                        context
                                        targetUrl
                                    }
                                }
                            }
                            # Aggregated state for statuses may be PENDING, FAILURE or SUCCESS.
                            state
                        }
                    }
                }
            }
        }
    }
}'''
# TODO(cyrille): Generate those from the query in a separated lib.
_Context = TypedDict('_Context', {'context': str, 'targetUrl': str}, total=False)
_StatusState = Literal['ERROR', 'EXPECTED', 'FAILURE', 'PENDING', 'SUCCESS']
_Rollup = TypedDict('_Rollup', {
    'contexts': _Connection[_Context],
    'state': _StatusState,
}, total=False)
_Commit = TypedDict('_Commit', {'statusCheckRollup': _Rollup}, total=False)
_PRCommit = TypedDict('_PRCommit', {'commit': _Commit})
_PullRequest = TypedDict('_PullRequest', {'commits': _Connection[_PRCommit]})
_Node = TypedDict('_Node', {'node': _PullRequest}, total=False)
_Response = TypedDict('_Response', {'data': _Node})


class _Request(TypedDict, total=False):
    text: str
    channel: str
    attachments: list[dict[str, Any]]


def _get_user(github_handle: str, config: _Config, as_channel: bool = False) -> str:
    try:
        user_id = config.github_to_slack[github_handle]
    except KeyError:
        if as_channel:
            raise
        # Use handle as username, for human-readability.
        return f'@{github_handle}'
    return f'@{user_id}' if as_channel else f'<@{user_id}>'


# TODO(cyrille): Consider using a repo-specific channel.
def _post_to_slack(prepared_request: _Request, config: _Config) -> None:
    response = requests.post(config.slack_url, json=prepared_request)
    response.raise_for_status()


def _send_review(
        number: str, title: str, github_author: str, demos: list[tuple[str, str]], config: _Config,
        *, github_reviewer: Optional[str] = None, reviewers: Optional[str] = None) -> None:
    from_author = f"{_get_user(github_author, config)}'s"
    text_start = 'CI tests passed' if not demos else \
        f'A <{demos[0][1]}|demo> is ready' if len(demos) == 1 else \
        f'Demos for <{">, <".join(demo[1] + "|" + demo[0] for demo in demos)}> are ready'
    request: _Request = {
        'text': f'{text_start} for {from_author} PR <https://reviewable.io/reviews'
        f'/{config.github_repo}/{number}|#{number}>.',
        'attachments': [{'text': title}],
    }
    if github_reviewer:
        request['channel'] = _get_user(github_reviewer, config, as_channel=True)
        request['text'] += ' You can start looking at it.'
    elif reviewers:
        request['text'] += f' Reviewers ({reviewers}) can start looking at it.'
    _post_to_slack(request, config)


def _get_more_info(pull_request: _GithubPullRequest, config: _Config) -> _ReviewInfo:
    """Whether the given commit needs a review, and if so on what demo."""

    response = requests.post('https://api.github.com/graphql', json={
        'query': _PULL_REQUEST_INFO_GRAPHQL_QUERY,
        'variables': {
            'prNodeId': pull_request['node_id'],
        },
    }, headers={'Authorization': f'token {config.github_token}'})
    response.raise_for_status()
    graphql_response: _Response = response.json()
    pr_data = graphql_response.get('data', {}).get('node')
    if not pr_data:
        # Unable to fetch PR data somehow, let's assume it needs reviewing.
        return _ReviewInfo(True)
    commits = pr_data.get('commits', {}).get('nodes', [])
    if not commits:
        # Couldn't find any commit to merge in this PR, it probably doesn't need any reviewing.
        return _ReviewInfo(False)
    rollup = commits[0].get('commit', {}).get('statusCheckRollup', {})
    if rollup.get('state') != 'PENDING':
        # Global state is either FAILURE or SUCCESS. In both cases, no need to ask for review.
        return _ReviewInfo(False)
    demo_url = next((
        status.get('targetUrl')
        for status in rollup.get('contexts', {}).get('nodes', [])
        if status.get('context') == 'bayesimpact/demo-frontend'), None)
    return _ReviewInfo(True, demo_url)


def ping_request_reviewers(
        pull_request: _GithubPullRequest, demos: list[tuple[str, str]], config: _Config, *,
        before: Optional[datetime.datetime] = None, should_get_more_info: bool = True) -> int:
    """Ping reviewers for a given PR."""

    if before and before < datetime.datetime.fromisoformat(
            pull_request['created_at'].removesuffix('Z')):
        return 0
    if pull_request.get('user', {}).get('login', '').endswith('[bot]'):
        # Not pinging for bot reviews.
        return 0
    all_reviewers = list(filter(None, {
        reviewer.get('login', '')
        for reviewer_list in (
            pull_request.get('requested_reviewers', []),
            pull_request.get('assignees', []))
        for reviewer in reviewer_list}))
    if not all_reviewers:
        return 0
    if should_get_more_info:
        # Make sure we actually want a review.
        should_review, real_demo_url = _get_more_info(pull_request, config)
        if not should_review:
            return 0
        if not demos and real_demo_url:
            demos = [('', real_demo_url)]
    pr_number = str(pull_request['number'])
    logging.info(
        'Pinging reviewers (of #%s) on Slack to tell them the Demo is ready…', pr_number)
    title = pull_request['title']
    author = pull_request['user']['login']
    ping_count = 0
    try:
        for reviewer in all_reviewers:
            # TODO(cyrille): Only ping the reviewers who haven't LGTM.
            # TODO(cyrille): Ping the author if there are no reviewers without LGTM.
            _send_review(pr_number, title, author, demos, config, github_reviewer=reviewer)
            ping_count += 1
    except (requests.HTTPError, KeyError):
        logging.warning('Pinging on default channel')
        # Unable to send the review to one of the reviewers, sending it to default channel.
        named_reviewers = ', '.join(_get_user(r, config) for r in sorted(all_reviewers))
        _send_review(pr_number, title, author, demos, config, reviewers=named_reviewers)
        ping_count += 1
    return ping_count


def ping_for_release(demo_url: str, callback_url: str, config: _Config) -> int:
    """Ping reviewers for a release demo."""

    _post_to_slack({
        'text': f'<!here> A demo for the release candidate {config.tag} is '
        f'<{demo_url}|ready for review>. See '
        f'<https://github.com/{config.github_repo}/compare/prod...{config.tag}|Git changes>.'
        f'After getting 2 manual approvals, <{callback_url}|approve the release workflow>.'
    }, config)
    return 1


def _get_pr_api_url(config: _Config, should_ping_stale: bool) -> Optional[str]:
    if should_ping_stale:
        return f'https://api.github.com/repos/{config.github_repo}/pulls?direction=asc'
    if not config.pr_number and not config.commit:
        return None
    pr_number = config.pr_number
    if not pr_number:
        # TODO(cyrille): Replace config.commit by CIRCLE_BRANCH, and use /pulls?head=branch instead.
        response = requests.get(
            'https://api.github.com/search/issues', params=dict(q=config.commit), headers={
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': f'token {config.github_token}',
            })
        response.raise_for_status()
        pr_number = str(response.json().get('number', ''))
    if not pr_number:
        return None
    return f'https://api.github.com/repos/{config.github_repo}/pulls/{pr_number}'


def ping_reviewers(demos: list[tuple[str, str]], ping_stale_reviews: bool, config: _Config) \
        -> int:
    """Send slack pings to the relevant people, if requirements are met."""

    if not config.github_token:
        logging.info('Need a Github token to get PR info, please set GITHUB_TOKEN')
        return 0
    if config.github_repo.strip('/') != config.github_repo:
        logging.info(
            'No Github repo specified, '
            'please set CIRCLE_PROJECT_USERNAME and CIRCLE_PROJECT_REPONAME')
        return 0
    query = _get_pr_api_url(config, ping_stale_reviews)
    if not query:
        logging.info('No PR to review, please set CIRCLE_PULL_REQUEST with a Github PR url.')
        return 0
    response = requests.get(query, headers={
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {config.github_token}',
    })
    response.raise_for_status()
    pull_requests = response.json()
    if not ping_stale_reviews:
        # Response to the /pulls/PR_NUMBER endpoint only has 1 PR in its answer.
        pull_requests = [pull_requests]
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    ping_count = 0
    for pull_request in pull_requests:
        ping_count += ping_request_reviewers(
            pull_request, demos, config, before=yesterday if ping_stale_reviews else None)
    return ping_count


def main(string_args: Optional[Sequence[str]] = None, env: Optional[dict[str, str]] = None) -> int:
    """Parse CLI arguments and ping reviewers.

    Return the number of ping sent (for testing purposes).
    # TODO(cyrille): Test differently and stop returning the number of pings.
    """

    parser = argparse.ArgumentParser(description='Ping reviewers for the current PR.')
    parser.add_argument(
        'demo_url', help='A URL where a demo for the changes can be found.', nargs='?')
    parser.add_argument(
        '--demo-name', default='default', help='The name of the demo given in demo_url.')
    parser.add_argument('--directory', '-d', help='''
        A folder where files represent different URLs to load.

        Each file should be named with the demo name (e.g. "frontend")
        and contain one line with the demo's URL.
    ''')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--release-callback')
    actions.add_argument('--ping-stale-reviews', action='store_true')
    args = parser.parse_args(string_args)
    config = _Config.from_env(env)
    if not config.slack_url:
        logging.info('Slack integration URL is missing, please set SLACK_INTEGRATION_URL')
        return 0
    if args.release_callback:
        return ping_for_release(args.demo_url, args.release_callback, config)
    demos: list[tuple[str, str]] = []
    if args.demo_url:
        demos.append((args.demo_name, args.demo_url))
    if args.directory:
        for filename in os.listdir(args.directory):
            with open(path.join(args.directory, filename)) as file:
                demos.append((filename, file.read().strip()))
    return ping_reviewers(demos, args.ping_stale_reviews, config)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
