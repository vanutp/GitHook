import os

from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', '8009'))
WORKERS = int(os.getenv('WORKERS', '1'))
DEBUG = bool(int(os.getenv('DEBUG', '0')))
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_USERNAME = os.getenv('BOT_USERNAME')

__all__ = ['HOST', 'PORT', 'WORKERS', 'DEBUG', 'BOT_TOKEN', 'API_ID', 'API_HASH', 'BOT_USERNAME']
