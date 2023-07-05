import asyncio
import os
import threading
from pprint import pprint

from aiogram.dispatcher import FSMContext
from aiogram import *

from src.commands import COMMANDS
from src.user import TipBotUser
from src import logger
from src.ui import *
from src import dp
from src.wallets.epic.epic_py.wallet.models import Transaction
from src.wallets.epic.epic_py.utils import benchmark


# /------ CREATE EPIC WALLET ------\ #
@dp.message_handler(commands=['create_epic_wallet'], state='*')
async def create_wallet(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.new_wallet(network='epic')


@dp.message_handler(commands=['send_epic'], state='*')
async def send_tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    amount = owner.ui.get_amount(message)
    receivers = owner.ui.get_receivers(message)[0]

    pprint(await owner.epic_wallet.send_via_epicbox(amount, receivers, message=f"Tip from {owner.name}"))


@dp.message_handler(commands=['deposit'], state='*')
async def deposit(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    address = owner.epic_wallet.config.epicbox_address
    transactions = list()

    await owner.ui.send_message(text=address, chat_id=owner.id)
    thread = threading.Thread(target=owner.epic_wallet.start_updater, args=(owner.epic_wallet.txs_updater, transactions))
    thread.start()
    # thread.join()
    #
    # if transactions:
    #     for tx in transactions:
    #         await owner.ui.send_message(text=f"✅ {tx.amount_credited} EPIC deposit received!", chat_id=owner.id)


@dp.message_handler(commands=['tx'], state='*')
async def get_txs(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    print('.')
    async with owner.epic_wallet.api_http_server as provider:
        # pprint(provider.retrieve_txs(refresh=False))
        pprint(await provider.retrieve_txs(refresh=False))


@dp.message_handler(commands=['send_epic2'], state='*')
async def send_tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    amount = owner.ui.get_amount(message)
    receivers = owner.ui.get_receivers(message)[0]

    response = await owner.epic_wallet.send_via_file(amount=amount)

    if response['error']:
        print(response)
        return

    init_tx_file = response['data']
    response_tx_file_path = receivers[0].epic_wallet.config.tx_files_directory
    _, response_tx_file_name = os.path.split(init_tx_file)
    response_tx_file = os.path.join(response_tx_file_path, response_tx_file_name)

    response_tx = await receivers[0].epic_wallet.receive_via_file(init_tx_file, response_tx_file)

    if response_tx['error']:
        print(response)
        return

    response_tx_file = response_tx['data']
    await owner.epic_wallet.finalize_file_tx(response_tx_file=response_tx_file)
    return
