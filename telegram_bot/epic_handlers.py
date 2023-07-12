import asyncio
from _decimal import Decimal
from pprint import pprint
import os

from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from aiogram import *

from src.commands import COMMANDS
from src import dp, tools, Database, storage, fees
from src.user import TipBotUser
from src.ui.interface import EpicWalletStates, WalletSettingsStates

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

        await owner.epic_wallet.db.wallets.post(params)
        # response = tools.api_call(query='save_wallet', url=Database.TIPBOT_URL, params=params, method='post')


@dp.message_handler(commands=['send_epic'], state='*')
async def send_tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    amount = owner.ui.get_amount(message)
    receivers = owner.ui.get_receivers(message)[0]
    message = await owner.ui.send_message(text=f"⏳ Sending transaction..")

    transactions = await owner.epic_wallet.send_epicbox(amount=amount, receivers=receivers, tx_type='tip', message=f"Tip from {owner.name}")

    for tx in transactions['success']:
        print(tx)
        text = f"✅ `{tools.num_as_str(tx['amount'])} EPIC` sent to *{tx['receiver']['mention']}*"
        await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)
        await owner.epic_wallet.db.transactions.post(tx)

    for tx in transactions['failed']:
        print(tx)
        receiver = tx['data']['receiver']['mention']

        if "NotEnoughFunds" in tx['msg']:
            print(tx['msg'])
            data = eval(tx['msg'])['message']
            data = eval(data.replace('NotEnoughFunds: ', ''))
            available = float(data['available_disp'])
            needed = float(data['needed_disp'])
            text = f"⚠️ Failed to send EPIC:\nNot enough balance: `{available}`, needed `{needed}`."
            await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)

        elif "is wallet api running under" in tx['msg']:
            text = f"⚠️ Failed to send EPIC to {receiver}."
            await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)


# /------ RUN EPICBOX DEPOSIT HANDLE ------\ #
@dp.callback_query_handler(text='epicbox_deposit', state='*')
async def epicbox_deposit(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    message = await owner.ui.epicbox_deposit()
    storage.update(key=f"{owner.id}_updater", value=True)
    storage.update(key=f"{owner.id}_updater_message", value=message)
    await EpicWalletStates.deposit.set()
    await owner.epic_wallet.start_updater(message)


# /------ CANCEL EPICBOX DEPOSIT HANDLE ------\ #
@dp.callback_query_handler(text='cancel_epicbox_deposit', state=EpicWalletStates.deposit)
async def cancel_epicbox_deposit(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    storage.update(f"{owner.id}_updater", value=False)
    message = storage.get(f"{owner.id}_updater_message")
    await owner.ui.cancel_state(state)
    await owner.ui.delete_message(message)
    storage.get(f"{owner.id}_updater_message", delete=True)


# /------ EPIC WALLET WITHDRAW FINALIZE CALLBACK ------\ #
@dp.callback_query_handler(text=['confirm_epic_withdraw'], state=EpicWalletStates.withdraw)
async def withdraw(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.message.chat.id)
    await owner.ui.finalize_epic_withdraw(state, query)


@dp.message_handler(commands=['balance_details'], state='*')
async def balance_details(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    message = await owner.ui.send_message(text=f"⏳ Getting EPIC Balance Details..")
    await EpicWalletStates.balance.set()

    balance = await owner.epic_wallet.get_balance(get_outputs=True)
    text = owner.ui.screen.epic_balance_details(balance)

    await owner.ui.cancel_state(state)
    await message.edit_text(text=text, parse_mode=ParseMode.MARKDOWN)


# /------ OUTPUTS HANDLE ------\ #
@dp.callback_query_handler(text='outputs', state='*')
async def outputs(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    await owner.ui.outputs(query=query, state=state)


# /------ CREATE NEW OUTPUTS 1/2 HANDLE ------\ #
@dp.callback_query_handler(text=['create_5', 'create_10'], state='*')
async def create_new_outputs_1_of_2(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    await owner.ui.create_new_outputs_1_of_2(query=query, state=state)


# /------ CREATE NEW OUTPUTS 2/2 HANDLE ------\ #
@dp.callback_query_handler(text='confirm_new_outputs', state='*')
async def create_new_outputs_2_of_2(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    await owner.ui.create_new_outputs_2_of_2(query=query, state=state)


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


@dp.message_handler(commands=['check'], state='*')
async def check_fee(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    # amount = owner.ui.get_amount(message)
    # outputs = 5
    # check = await owner.epic_wallet.calculate_fees(amount, num_change_outputs=outputs)
    check = await owner.epic_wallet.create_outputs(2, refresh=False)
    pprint(check)
