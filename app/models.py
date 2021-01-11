from enum import Enum
from typing import List, Optional

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
    ref_url: str
    head_sha: str
    head_url: str
    author: str
    commits: List[Commit]
    repo: Repository


class Status(str, Enum):
    unknown = 'unknown'
    running = 'running'
    failed = 'failed'
    success = 'success'
    cancelled = 'cancelled'


class PipelineEvent(BaseModel):
    id: int
    url: Optional[str]
    status: Status
    repo: Repository


class JobEvent(BaseModel):
    id: int
    name: str
    url: str
    status: Status
    pipeline: PipelineEvent
    repo: Repository
