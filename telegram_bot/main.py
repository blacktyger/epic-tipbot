import itertools
import asyncio

from aiogram.dispatcher import FSMContext
from aiogram import *

from src.wallets.vite import faq_screen, welcome_screen
from src.keys import FEE_SEED, ADDRESS_ID, TOKEN
from src import logger, tools, dp
from src.commands import COMMANDS
from src.settings import Tipbot
from src.user import TipBotUser
from src.ui import *

# Import Handlers for Vite and Epic operations
import vite_handlers
import epic_handlers


__version__ = '2.5'
storage = tools.storage


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
    response = owner.register()
    await owner.ui.new_wallet(netowrk='vite', payload=response)


# /------ WALLET GUI HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['wallet'], state='*')
async def wallet(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.show_wallet(state=state, message=message)


# /------ WALLET GUI SUPPORT ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='support'), state='*')
async def gui_support(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    print(owner)
    await owner.ui.show_support(query=query)


# /------ START/HELP HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['start'])
async def start(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await welcome_screen(user=owner, message=message)


# /------ FAQ HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['faq'])
async def faq(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await faq_screen(user=owner, message=message)


# /------ CANCEL ANY STATE HANDLE ------\ #
@dp.callback_query_handler(text='cancel_any', state='*')
async def cancel_any_state(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
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


# /------ START MAIN LOOP ------\ #
if __name__ == '__main__':
    logger.info(f"Starting EpicTipBot({TOKEN.split(':')[0]})")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
