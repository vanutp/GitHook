import json
from html import escape
from time import time
from typing import Optional, Union

from fastapi import APIRouter, Body, Header
from fastapi.responses import Response
from starlette.responses import JSONResponse
from telethon import Button

from app import bot
from app.env import DEBUG
from app.models import GitService
from app.utils import format_push_event, format_pipeline_event

router = APIRouter()

if DEBUG:
    @router.post('/debug/{chat_id}')
    async def debug(chat_id: int,
                    x_gitlab_event: Optional[str] = Header(None), x_github_event: Optional[str] = Header(None),
                    payload: dict = Body(...)):
        filename = f'{int(time())}'
        if x_gitlab_event:
            filename = f'gl-{x_gitlab_event}-{filename}'
        elif x_github_event:
            filename = f'gh-{x_github_event}-{filename}'
        else:
            filename = f'rq-{filename}'
        filename += '.json'
        file = await bot.upload_file(json.dumps(payload).encode(), file_name=filename)
        await bot.send_file(chat_id, file)
        return 'OK'

pipeline_responses = {
    'running': '<b>🚀 Pipeline started</b>',
    'failed': '<b>😔 Pipeline failed</b>',
    'success': '<b>🥳 Pipeline succeed!</b>',
    'cancelled': '<b>✋ Pipeline cancelled</b>',
    'unknown': '<b>Unknown pipeline status!</b>'
}


@router.post('/trigger/{chat_id}')
async def trigger(chat_id: Union[int, str], show_author_name: Optional[bool] = True,
                  multiline_commit: Optional[bool] = True, max_commits: Optional[int] = 6,
                  x_gitlab_event: Optional[str] = Header(None), x_github_event: Optional[str] = Header(None),
                  payload: dict = Body(...)):
    if x_gitlab_event:
        service = GitService.gl
    elif x_github_event:
        service = GitService.gh
    else:
        return JSONResponse({'detail': 'Unknown git service'}, 400)
    try:
        await bot.get_input_entity(chat_id)
    except ValueError:
        return JSONResponse({'detail': f'Telethon: Could not find input entity for {chat_id}'}, 400)
    if x_github_event == 'ping':
        return Response(None, 204)
    if x_gitlab_event == 'Push Hook' or x_github_event == 'push':  # TODO: редизайн сообщения
        event = format_push_event(service, payload)
        ref = f'{escape(event.repo.name)}:{escape(event.ref.split("/")[-1])}'
        if event.forced:
            head = f'<a href="{event.repo.url}/commit/{event.head_sha}">{escape(event.head_sha[:7])}</a>'
            if show_author_name:
                head += f'\n- by {event.author}'
            await bot.send_message(chat_id, f'🔨 Force pushed. <b>{ref}</b> is now at {head}', link_preview=False)
        else:
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
            await bot.send_message(chat_id, text, link_preview=False)
    elif x_gitlab_event == 'Pipeline Hook' or x_github_event == 'check_run':  # TODO: gh actions, параметры
        event = format_pipeline_event(service, payload)
        await bot.send_message(
            chat_id, pipeline_responses[event.status],
            buttons=[[
                Button.url(event.repo.name, event.repo.url),
                Button.url(f'#{event.id}', event.url)
            ]]
        )
    else:
        return JSONResponse({'detail': 'Unknown event'}, 400)
    return Response(None, 204)
