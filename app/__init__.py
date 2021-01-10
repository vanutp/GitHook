import logging
import os

from fastapi import FastAPI
from telethon import TelegramClient, events
from telethon.tl.custom import Message

from app.env import *

bot = TelegramClient('bot', API_ID, API_HASH)
bot.parse_mode = 'html'
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]', level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@bot.on(events.NewMessage(pattern=f'^/get_entity@{BOT_USERNAME}$'))
async def get_entity(message: Message):
    await bot.get_input_entity(message.chat)
    await message.reply('OK')


@app.on_event('startup')
async def connect_telethon():
    await bot.connect()
    await bot.sign_in(bot_token=BOT_TOKEN)


from app.routes import router

app.include_router(router)
