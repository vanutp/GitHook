from html import escape

from app.models import GitService, PushEvent, Repository, Commit, PipelineEvent, Status, JobEvent


def format_push_event(service: GitService, payload: dict) -> PushEvent:
    event = PushEvent.construct()
    event.repo = Repository.construct()
    event.ref = payload['ref']
    short_ref = event.ref.split("/")[-1]
    if service == GitService.gh:
        event.repo.url = payload['repository']['html_url']
        event.repo.name = payload['repository']['full_name']
        event.forced = payload['forced']
        event.author = payload['pusher']['name']
        event.ref_url = f'{event.repo.url}/tree/{short_ref}'
    elif service == GitService.gl:
        event.repo.url = payload['project']['web_url']
        event.repo.name = payload['project']['path_with_namespace']
        event.forced = False
        event.author = payload['user_name']
        event.ref_url = f'{event.repo.url}/-/tree/{short_ref}'
    event.head_sha = payload['after']
    event.head_url = f'{event.repo.url}/commit/{event.head_sha}'
    event.commits = []
    for commit in payload['commits']:
        event.commits.append(
            Commit(
                id=commit['id'],
                message=commit['message'].strip('\n'),
                author=commit['author']['name'],
                url=commit['url']
            )
        )
    return event


def format_pipeline_event(service: GitService, payload: dict) -> PipelineEvent:
    event = PipelineEvent.construct()
    event.repo = Repository.construct()
    if service == GitService.gl:
        event.id = payload['object_attributes']['id']
        event.status = Status[payload['object_attributes']['status']]
        event.repo.url = payload['project']['web_url']
        event.repo.name = payload['project']['path_with_namespace']
        event.url = f'{event.repo.url}/-/pipelines/{event.id}'
    return event


def _convert_github_status(status: str, conclusion: str) -> Status:
    if status in ['queued', 'in_progress']:
        return Status.running
    if status == 'completed' and conclusion == 'success':
        return Status.success
    if status == 'completed' and conclusion in ['failure', 'timed_out']:
        return Status.failed
    if status == 'completed' and conclusion == 'cancelled':
        return Status.cancelled
    return Status.unknown


def format_job_event(service: GitService, payload: dict) -> JobEvent:
    event = JobEvent.construct()
    event.repo = Repository.construct()
    event.pipeline = PipelineEvent.construct()
    if service == GitService.gh:
        event.id = payload['check_run']['id']
        event.name = payload['check_run']['name']
        event.repo.url = payload['repository']['html_url']
        event.repo.name = payload['repository']['full_name']
        event.url = payload['check_run']['html_url'] + '?check_suite_focus=true'
        event.status = _convert_github_status(payload['check_run']['status'], payload['check_run']['conclusion'])

        check_suite = payload['check_run']['check_suite']
        event.pipeline.id = check_suite['id']
        event.pipeline.repo = event.repo
        event.pipeline.status = _convert_github_status(check_suite['status'], check_suite['conclusion'])
    return event


def format_old_style_commit_message(event: PushEvent,
                                    show_author_name: bool, multiline_commit: bool, max_commits: int) -> str:
    ref = escape(f'{event.repo.name}:{event.ref.split("/")[-1]}')
    if event.forced:
        head = f'<a href="{event.repo.url}/commit/{event.head_sha}">{escape(event.head_sha[:7])}</a>'
        if show_author_name:
            head += f'\n- by {escape(event.author)}'
        return f'🔨 Force pushed. <b>{ref}</b> is now at {head}'
    if len(event.commits) <= max_commits or max_commits == 0:
        commits = []
        for commit in event.commits:
            msg = escape(commit.message)
            if not multiline_commit:
                msg = msg.split('\n')[0]
            msg = msg.strip('\n')
            commit_msg = f'<a href="{escape(commit.url)}">{escape(commit.id[:7])}</a>: <code>{msg}</code>'
            if show_author_name:
                commit_msg += f'\n- by {escape(commit.author)}'
            commits.append(commit_msg)
        commits = ':\n\n' + '\n'.join(commits)
    else:
        commits = ''
    commits_word = 'commit' if len(event.commits) == 1 else 'commits'
    text = f'🔨 {len(event.commits)} new {commits_word} to <b>{ref}</b>'
    if len(text + commits) <= 4096:
        text += commits
    return text
