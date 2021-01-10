from app.models import GitService, PushEvent, Repository, Commit, PipelineEvent, PipelineStatus


def format_push_event(service: GitService, payload: dict) -> PushEvent:
    event = PushEvent.construct()
    event.repo = Repository.construct()
    if service == GitService.gh:
        event.repo.url = payload['repository']['html_url']
        event.repo.name = payload['repository']['full_name']
        event.forced = payload['forced']
        event.author = payload['pusher']['name']
    elif service == GitService.gl:
        event.repo.url = payload['project']['web_url']
        event.repo.name = payload['project']['path_with_namespace']
        event.forced = False
        event.author = payload['user_name']
    event.head_sha = payload['after']
    event.ref = payload['ref']
    event.commits = []
    for commit in payload['commits']:
        event.commits.append(
            Commit(
                id=commit['id'],
                message=commit['message'],
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
        event.status = PipelineStatus[payload['object_attributes']['status']]
        event.repo.url = payload['project']['web_url']
        event.repo.name = payload['project']['path_with_namespace']
        event.url = f'{event.repo.url}/-/pipelines/{event.id}'
    elif service == GitService.gh:
        event.id = payload['check_run']['id']
        event.repo.url = payload['repository']['html_url']
        event.repo.name = payload['repository']['full_name']
        event.url = payload['check_run']['html_url'] + '?check_suite_focus=true'
        action = payload['action']
        status = payload['check_run']['status']
        conclusion = payload['check_run']['conclusion']
        if action in ['created', 'rerequested']:
            event.status = PipelineStatus.running
        elif status == 'completed' and conclusion == 'success':
            event.status = PipelineStatus.success
        elif status == 'completed' and conclusion in ['failure', 'timed_out']:
            event.status = PipelineStatus.failed
        elif status == 'completed' and conclusion == 'cancelled':
            event.status = PipelineStatus.cancelled
        else:
            event.status = PipelineStatus.unknown
    return event
