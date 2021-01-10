from hypercorn import Config
from hypercorn.asyncio import serve

from app import bot, app
from app.env import *

if __name__ == '__main__':
    config = Config()
    config.bind = f'{HOST}:{PORT}'
    config.workers = WORKERS
    config.debug = DEBUG
    bot.loop.run_until_complete(serve(app, config))
