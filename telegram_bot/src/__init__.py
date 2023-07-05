from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher

from .settings import Database, Tipbot
from .logger_ import logger
from .keys import TOKEN
from . import tools


try:
    scheduler = AsyncIOScheduler()
except:
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")

scheduler.start()
DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL


bot = Bot(token=TOKEN)


# /------ AIOGRAM BOT SETTINGS ------\ #
storage = tools.storage

dp = Dispatcher(bot, storage=tools.temp_storage())

