import json
from enum import Enum
from html import escape
from time import time
from typing import Optional, Union

from fastapi import APIRouter, Body, Header
from fastapi.responses import Response
from starlette.responses import JSONResponse
from telethon import Button

from app import bot
from app.env import DEBUG
from app.models import GitService, Error
from app.utils import format_push_event, format_pipeline_event, format_job_event, format_old_style_commit_message

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

job_responses = {
    'running': '<b>🚀 Job "{job}" started</b>',
    'failed': '<b>😔 Job "{job}" failed</b>',
    'success': '<b>🥳 Job "{job}" succeed!</b>',
    'cancelled': '<b>✋ Job "{job}" cancelled</b>',
    'unknown': '<b>Job "{job}" has unknown status!</b>'
}


class PushMessageStyle(str, Enum):
    old = 'old'
    new = 'new'


@router.post('/trigger/{chat_id}',
             responses={
                 204: {'description': 'OK'},
                 400: {'model': Error}
             },
             status_code=204)
async def trigger(chat_id: Union[int, str],
                  push_message_style: Optional[PushMessageStyle] = PushMessageStyle.new,
                  show_author_name: Optional[bool] = True, multiline_commit: Optional[bool] = True,
                  max_commits: Optional[int] = 5,
                  x_gitlab_event: Optional[str] = Header(None), x_github_event: Optional[str] = Header(None),
                  payload: dict = Body(...)):
    """
    Webhook url

    Arguments:
    - push_message_style (`str`, optional, default 'new'):
        'old' or 'new'
    - show_author_name (`bool`, optional, default True):
        Only for push_message_style == 'old'
    - multiline_commit (`bool`, optional, default True):
        Only for push_message_style == 'old'
    - max_commits (`bool`, optional, default 5):
        Maximum 5 in push_message_style == 'new'
    - x_gitlab_event (`str`)
    - x_github_event (`str`)
    - payload (`dict`)
    """
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
        if push_message_style == PushMessageStyle.old:
            await bot.send_message(
                chat_id,
                format_old_style_commit_message(event, show_author_name, multiline_commit, max_commits),
                link_preview=False
            )
        elif push_message_style == PushMessageStyle.new:
            if max_commits == 0 or max_commits > 5:
                max_commits = 5
            ref = f'{event.repo.name}:{event.ref.split("/")[-1]}'
            if event.forced:
                await bot.send_message(
                    chat_id, f'🔨 <b>{escape(event.author)} force pushed</b>',
                    buttons=[[
                        Button.url(ref, event.ref_url),
                        Button.url(event.head_sha[:7], event.head_url)
                    ]]
                )
            else:
                for commit in event.commits[:max_commits]:
                    await bot.send_message(
                        chat_id, f'📝 <b>New commit by {escape(event.author)}</b>\n'
                                 f'<pre>{escape(commit.message)}</pre>',
                        buttons=[[
                            Button.url(ref, event.ref_url),
                            Button.url(event.head_sha[:7], event.head_url)
                        ]]
                    )
        return Response(None, 204)
    elif x_gitlab_event == 'Pipeline Hook':
        event = format_pipeline_event(service, payload)
        await bot.send_message(
            chat_id, pipeline_responses[event.status],
            buttons=[[
                Button.url(event.repo.name, event.repo.url),
                Button.url('Pipeline', event.url)
            ]]
        )
        return Response(None, 204)
    elif x_github_event == 'check_run':
        event = format_job_event(service, payload)
        await bot.send_message(
            chat_id, job_responses[event.status].format(job=event.name, pipeline=f'#{event.pipeline.id}'),
            buttons=[[
                Button.url(event.repo.name, event.repo.url),
                Button.url('Pipeline', event.url)
            ]]
        )
        return Response(None, 204)
    return JSONResponse({'detail': 'Unknown event'}, 400)

