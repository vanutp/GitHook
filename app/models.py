from enum import Enum
from typing import List

from pydantic import BaseModel


class GitService(Enum):
    gh = 'gh'  # Github
    gl = 'gl'  # Gitlab
    # gt = 'gt'  # Gitea


class Commit(BaseModel):
    id: str
    message: str
    author: str
    url: str


class Repository(BaseModel):
    url: str
    name: str


class PushEvent(BaseModel):
    forced: bool
    ref: str
    head_sha: str
    author: str
    commits: List[Commit]
    repo: Repository


class PipelineStatus(str, Enum):
    unknown = 'unknown'
    running = 'running'
    failed = 'failed'
    success = 'success'
    cancelled = 'cancelled'


class PipelineEvent(BaseModel):
    id: int
    url: str
    status: PipelineStatus
    repo: Repository
