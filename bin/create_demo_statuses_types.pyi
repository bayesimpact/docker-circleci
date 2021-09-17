import typing
from typing import Generic, Literal, Optional, Protocol, Sequence, Set, TypedDict

# TODO(cyrille): Generate those from the query in a separated lib.
_T = typing.TypeVar('_T')


class _Connection(Protocol, Generic[_T]):
    def __getitem__(self, nodes: Literal['nodes']) -> list[_T]:
        ...

    def get(self, nodes: Literal['nodes'], default: list[_T]) -> list[_T]:
        ...


_Context = TypedDict('_Context', {'context': str, 'targetUrl': str}, total=False)
_DeploymentState = Literal[
    'ABANDONED',
    'ACTIVE',
    'DESTROYED',
    'ERROR',
    'FAILURE',
    'IN_PROGRESS',
    'INACTIVE',
    'PENDING',
    'QUEUED',
    'WAITING',
]
_DeploymentStatus = TypedDict('_DeploymentStatus', {'environmentUrl': str}, total=False)
_Deployment = TypedDict('_Deployment', {
    'description': str,
    'state': _DeploymentState,
    'latestStatus': _DeploymentStatus,
}, total=False)
_DeployedEvent = TypedDict('_DeployedEvent', {'deployment': _Deployment})
_PullRequest = TypedDict('_PullRequest', {'timelineItems': _Connection[_DeployedEvent]})
_Repository = TypedDict('_Repository', {'pullRequest': _PullRequest})
_Data = TypedDict('_Data', {'repository': _Repository}, total=False)
_Response = TypedDict('_Response', {'data': _Data})
