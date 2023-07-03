import asyncio
import os

from aiogram.dispatcher import FSMContext
from aiogram import *

from src.commands import COMMANDS
from src.user import TipBotUser
from src import logger
from src.ui import *
from src import dp


# /------ CREATE EPIC WALLET ------\ #
@dp.message_handler(commands=['create_epic_wallet'], state='*')
async def create_wallet(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.new_wallet(network='epic')


@dp.message_handler(commands=['run_epicbox'], state='*')
async def run_epicbox(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    loop = asyncio.get_event_loop()

    def send_notification(text: str):
        ignore = ['Still receiving data', 'Starting epicbox', 'log4rs is initialized', 'This is Epic Wallet version', 'Using wallet configuration']
        if not any([msg in text for msg in ignore]):
            asyncio.run_coroutine_threadsafe(Interface.send_message(text=text, chat_id=owner.id), loop)

    owner.epic_wallet.run_epicbox(callback=send_notification, force_run=True, logger=logger)


@dp.message_handler(commands=['send_epic'], state='*')
async def send_tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    amount = owner.ui.get_amount(message)
    receivers = owner.ui.get_receivers(message)[0]

    response = owner.epic_wallet.send_via_file(amount=amount)

    if response['error']:
        return

    init_tx_file = response['data']
    response_tx_file_path = receivers[0].epic_wallet.config.tx_files_directory
    _, response_tx_file_name = os.path.split(init_tx_file)
    response_tx_file = os.path.join(response_tx_file_path, response_tx_file_name)

    response_tx = receivers[0].epic_wallet.receive_via_file(init_tx_file, response_tx_file)

    if response_tx['error']:
        return

    response_tx_file = response_tx['data']

    print(owner.epic_wallet.finalize_file_tx(response_tx_file=response_tx_file))
