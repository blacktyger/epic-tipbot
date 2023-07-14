import itertools
import asyncio

from aiogram.dispatcher import FSMContext
from aiogram import *
from aiogram.types import ParseMode

from src.keys import FEE_SEED, ADDRESS_ID, TOKEN
from dev_tools import WithdrawWallet
from src import logger, tools, dp, database, ui
from src.commands import COMMANDS
from src.settings import Tipbot
from src.user import TipBotUser

# Import Handlers for Vite and Epic operations
import vite_handlers
import epic_handlers


__version__ = '2.5'


# /------ MAINTENANCE HANDLE ------\ #
if Tipbot.MAINTENANCE:
    all_commands = tuple(itertools.chain(*COMMANDS.values()))
    print(all_commands)

    @dp.message_handler(lambda message: message.text.startswith(all_commands))
    @dp.message_handler(commands=all_commands)
    async def maintenance(message: types.Message):
        owner = TipBotUser.from_obj(message.from_user)
        await owner.ui.maintenance(message)


# /------ CREATE ACCOUNT HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['create'])
async def create_account(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    response = await owner.register()
    await owner.ui.new_wallet(network='vite', payload=response)


# /------ WALLET GUI HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['wallet'], state='*')
async def wallet(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.show_wallet(state=state, message=message)


# /------ WALLET REFRESH HANDLE ------\ #
@dp.callback_query_handler(ui.wallet_cb.filter(action='refresh'), state='*')
async def refresh(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.delete_message(query.message)
    await owner.ui.show_wallet(state)


# /------ WALLET GUI DEPOSIT STEP 1/2 ------\ #
@dp.callback_query_handler(ui.wallet_cb.filter(action='deposit'), state='*')
async def deposit(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.deposit()


# /------ WALLET GUI WITHDRAW STEP 0/3 ------\ #
@dp.callback_query_handler(ui.wallet_cb.filter(action='withdraw'), state='*')
async def gui_withdraw(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.withdraw_0_of_3(state=state, query=query)


# /------ WALLET GUI WITHDRAW STEP 1/3 ------\ #
@dp.callback_query_handler(text=['withdraw_epic', 'withdraw_vite'], state=ui.SharedStates.withdraw)
async def gui_withdraw_network(query: types.CallbackQuery, state: FSMContext):
    network = query.data.split('_')[-1]
    await state.update_data({'network': network})
    owner = TipBotUser(id=query.message.chat.id)
    await owner.ui.withdraw_1_of_3(state=state, query=query)


# /------ WALLET GUI WITHDRAW STEP 2/3 ------\ #
@dp.message_handler(state=ui.SharedStates.ask_for_address)
async def handle_withdraw_address(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.withdraw_2_of_3(state=state, message=message)


# /------ WALLET GUI WITHDRAW STEP 3/3 ------\ #
@dp.message_handler(state=ui.SharedStates.ask_for_amount)
async def handle_withdraw_amount(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.withdraw_3_of_3(state=state, message=message)


# /------ WALLET SETTINGS HANDLE ------\ #
@dp.callback_query_handler(ui.wallet_cb.filter(action='settings'), state='*')
async def settings(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.settings(state=state, query=query)


# /------ START/HELP HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['start'])
async def start(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.welcome_screen(user=owner, message=message)


# /------ FAQ HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['faq'])
async def faq(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.faq_screen(user=owner, message=message)


# /------ CANCEL ANY STATE HANDLE ------\ #
@dp.callback_query_handler(text='cancel_any', state='*')
async def cancel_any_state(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    await owner.ui.cancel_state(state=state, query=query)


# /------ CLOSE ANY MESSAGE HANDLE ------\ #
@dp.callback_query_handler(text='close_any', state='*')
async def close_any_message(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    data = await state.get_data()

    if 'qr_message' in data:
        await owner.ui.delete_message(data['qr_message'])

    await owner.ui.delete_message(query.message)
    await owner.ui.cancel_state(state=state, query=query)


# /------ GET UPDATE INFO HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['update_info'])
async def update_info(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.update_info()


# /------ SEND MESSAGE TO USERS HANDLE ------\ #
@dp.message_handler(commands=['spam_message'], state='*')
async def spam_message(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.spam_message(message, send_wallet=True)


async def on_startup(*args):
    """
    Task to be fired up when main script is started.
    """
    # Periodic task: save to temp storage EPIC vs USD market price
    asyncio.create_task(tools.MarketData().price_epic_vs(currency='USD'))
    logger.info('Starting "EPIC USD" fetching price task')

    # Periodic task to update fee wallet
    asyncio.create_task(tools.fee_wallet_update(FEE_SEED, ADDRESS_ID))
    logger.info('Starting updating fee_wallet task')

    # # Run withdraw wallet instance updater
    asyncio.create_task(WithdrawWallet().start_updater())


async def on_shutdown(*args):
    # Close Django database session
    session = await database.get_client_session()
    await session.close()


# /------ START MAIN LOOP ------\ #
if __name__ == '__main__':
    tools.delete_lock_files()
    logger.info(f"Starting EpicTipBot({TOKEN.split(':')[0]})")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
