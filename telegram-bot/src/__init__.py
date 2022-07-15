from aiogram import Bot

from .settings import Database, Tipbot, MarketData
from .logger_ import logger
from .keys import TOKEN

DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL


logger = logger
bot = Bot(token=TOKEN)
