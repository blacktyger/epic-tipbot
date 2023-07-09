import asyncio
import json
from _decimal import Decimal
from pprint import pprint
import threading
import queue
import os

from aiogram.dispatcher import FSMContext
from aiogram import *
from aiogram.types import ParseMode

from src.commands import COMMANDS
from src.user import TipBotUser
from src import logger
from src.ui import *
from src import dp, tools, Database
from src.wallets.epic.epic_py.wallet.models import Transaction
from src.wallets.epic.epic_py.utils import benchmark

"""
User actions:
WALLET:
    create new epic wallet -> db save wallet (owner, network, encrypted mnemonics, address, extra data)
    get mnemonics -> db get mnemonics
    
TRANSACTIONS:
    deposit tx -> db save deposit transaction (owner, asset, amount, type_of, status, extra data(tx_id), message)
    tip tx -> db save tip transaction (owner, asset, amount, type_of, status, extra data(tx_id), message)
    withdraw tx -> db save withdraw transaction (owner, asset, amount, type_of, status, extra data(tx_id), message)
"""


# response = self._api_call('send_transaction', transaction, method='post', api_url=self.API_URL2)


# /------ CREATE EPIC WALLET ------\ #
@dp.message_handler(commands=['create_epic_wallet'], state='*')
async def create_wallet(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    response = await owner.ui.new_wallet(network='epic')

    if not response['error']:
        wallet = response['data']

        params = {
            'user': owner.params(),
            'network': 'EPIC',
            'address': wallet.config.epicbox_address,
            'mnemonics': wallet.mnemonics
            }

        response = tools.api_call(query='save_wallet', url=Database.TIPBOT_URL, params=params, method='post')


@dp.message_handler(commands=['send_epic'], state='*')
async def send_tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    amount = owner.ui.get_amount(message)
    receivers = owner.ui.get_receivers(message)[0]
    message = await owner.ui.send_message(text=f"⏳ Sending transaction..")

    transactions = await owner.epic_wallet.send_epicbox(amount=amount, receivers=receivers, tx_type='tip', message=f"Tip from {owner.name}")

    for tx in transactions['success']:
        print(tx)
        text = f"✅ Sent {tx['amount']} EPIC to {tx['receiver']['mention']}"
        await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)
        response = tools.api_call(query='save_transaction', url=Database.TIPBOT_URL, params=tx, method='post')

    for tx in transactions['failed']:
        print(tx)
        receiver = tx['data']['receiver']['mention']

        if "NotEnoughFunds" in tx['msg']:
            print(tx['msg'])
            data = eval(tx['msg'])['message']
            data = eval(data.replace('NotEnoughFunds: ', ''))
            available = float(data['available_disp'])
            needed = float(data['needed_disp'])
            text = f"⚠️ Failed to send EPIC to {receiver}:\nNot enough balance: `{available}`, needed `{needed}`."
            await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)

        elif "is wallet api running under" in tx['msg']:
            text = f"⚠️ Failed to send EPIC to {receiver}."
            await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['deposit'], state='*')
async def deposit(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    address = owner.epic_wallet.config.epicbox_address

    message = await owner.ui.send_message(text=f"⏳ Waiting for deposit..\n\n{address}")
    await owner.epic_wallet.start_updater(message)


@dp.message_handler(commands=['withdraw'], state='*')
async def withdraw(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    amount = round(owner.ui.get_amount(message) + 0.01, 8)
    address = owner.ui.get_address(message)

    if amount and address:
        message = await owner.ui.send_message(text=f"⏳ Withdrawing `{float(amount)} EPIC`..")
        transactions = await owner.epic_wallet.send_epicbox(amount, address=address, tx_type='withdraw', message=f"Withdraw from @EpicTipBot")

        for tx in transactions['success']:
            amount += tx['data']['fee']
            text = f"✅ Sent  `{amount} EPIC`  (including fees) to `{tx['address']}`"
            await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)
            tools.api_call(query='save_transaction', url=Database.TIPBOT_URL, params=tx, method='post')

        for tx in transactions['failed']:
            print(tx)
            receiver = tx['data']['address']

            if "NotEnoughFunds" in tx['msg']:
                print(tx['msg'])
                data = eval(tx['msg'])['message']
                data = eval(data.replace('NotEnoughFunds: ', ''))
                available = float(data['available_disp'])
                needed = float(data['needed_disp'])
                text = f"⚠️ Failed to send EPIC to {receiver}:\nNot enough balance: `{available}`, needed `{needed}`."
                await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)

            elif "is wallet api running under" in tx['msg']:
                text = f"⚠️ Failed to send EPIC to {receiver}."
                await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)
    else:
        await owner.ui.send_message(text=f"🟡 Invalid amount ot address")


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


@dp.message_handler(commands=['tx'], state='*')
async def get_txs(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    print('.')
    async with owner.epic_wallet.api_http_server as provider:
        # pprint(provider.retrieve_txs(refresh=False))
        pprint(await provider.retrieve_txs(refresh=False))
