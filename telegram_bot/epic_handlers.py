from aiogram.dispatcher import FSMContext
from aiogram import *

from src.commands import COMMANDS
from src.user import TipBotUser
from src.ui import *
from src import dp


# /------ CREATE EPIC WALLET ------\ #
@dp.message_handler(commands=['create_epic_wallet'], state='*')
async def create_wallet(message: types.Message):
    print('.')
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.new_wallet(network='epic')