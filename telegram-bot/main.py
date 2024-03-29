from aiogram.dispatcher import FSMContext
from aiogram import *
from aiogram.types import ParseMode
from aiogram.utils import markdown

from src.settings import Database, MarketData, Tipbot
from src import bot, logger, tools
from src.commands import COMMANDS
from src.user import TipBotUser
from src.wallet import *
from src.ui import *


__version__ = '2.0'

# /------ AIOGRAM BOT SETTINGS ------\ #
dp = Dispatcher(bot, storage=tools.temp_storage())

DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL
COMMANDS = COMMANDS
PRICE = MarketData()


# /------ CREATE ACCOUNT HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['create'])
async def create_account(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    response = owner.register()
    await owner.ui.new_wallet(response)


# /------ WALLET GUI HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['wallet'], state='*')
async def wallet(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.show_wallet(state=state, message=message)


# /------ WALLET GUI DEPOSIT ADDRESS STEP 1/1 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='deposit'), state='*')
async def gui_deposit(query: types.CallbackQuery, callback_data: dict):
    owner = TipBotUser(id=callback_data['user'])
    await owner.wallet.show_deposit(query=query)


# /------ WALLET GUI WITHDRAW STEP 1/3 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='withdraw'), state='*')
async def gui_withdraw(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.withdraw_1_of_3(state=state, query=query)


# /------ WALLET GUI WITHDRAW STEP 2/3 ------\ #
@dp.message_handler(state=WithdrawStates.ask_for_address)
async def handle_withdraw_address(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.withdraw_2_of_3(state=state, message=message)


# /------ WALLET GUI WITHDRAW STEP 3/3 ------\ #
@dp.message_handler(state=WithdrawStates.ask_for_amount)
async def handle_withdraw_amount(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.withdraw_3_of_3(state=state, message=message)


# /------ WALLET GUI WITHDRAW EPIC FINALIZE CALLBACK ------\ #
@dp.callback_query_handler(text=['confirm_withdraw'], state=[DonateStates.confirmation,
                                                             WithdrawStates.confirmation])
async def handle_withdraw_final(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.message.chat.id)
    await owner.wallet.withdraw(state=state, query=query)


# /------ WALLET GUI SEND STEP 1/3 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='send'), state='*')
async def gui_send(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.send_to_user_1_of_3(state=state, query=query)


# /------ WALLET GUI SEND STEP 2/3 ------\ #
@dp.message_handler(state=SendStates.ask_for_recipient)
async def handle_send_recipient(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.send_to_user_2_of_3(state=state, message=message)


# /------ WALLET GUI SEND STEP 3/3 ------\ #
@dp.message_handler(state=SendStates.ask_for_amount)
async def handle_send_amount(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.send_to_user_3_of_3(state=state, message=message)


# /------ WALLET GUI SEND TO USER FINALIZE CALLBACK ------\ #
@dp.callback_query_handler(text=['confirm_send'], state=[SendStates.confirmation])
async def handle_send_epic(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.message.chat.id)
    await owner.wallet.send_to_users(state=state, query=query)


# /------ WALLET GUI DONATE STEP 1/2 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='donate'), state='*')
async def gui_donate(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.donate_1_of_2(state=state, query=query)


# /------ WALLET GUI DONATE STEP 2/2 ------\ #
@dp.callback_query_handler(text=['donate_1', 'donate_5', 'donate_10'],
                           state=DonateStates.ask_for_amount)
async def handle_donate_amount(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.message.chat.id)
    await owner.ui.donate_2_of_2(state=state, query=query)


# /------ WALLET GUI SUPPORT STEP 1/1 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='support'), state='*')
async def gui_support(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.show_support(query=query)


# /------ TIP EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['tip'])
@dp.message_handler(lambda message: message.text.startswith(('tip', 'Tip'))
                    and 2 < len(message.text.split(' ')) < 10)
async def tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    if owner.is_registered:
        await owner.ui.send_tip_cmd(message=message)


# /------ START/HELP HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['start'])
async def start(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await vite_wallet.welcome_screen(user=owner, message=message)


# /------ FAQ HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['faq'])
async def faq(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await vite_wallet.faq_screen(user=owner, message=message)


# /------ CONFIRM FAILED TIP ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='confirm_failed_tip'), state='*')
async def confirm_failed_tip(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    if owner.id == int(callback_data['user']):
        await query.message.delete()


# /------ CANCEL ANY STATE HANDLE ------\ #
@dp.callback_query_handler(text='cancel_any', state='*')
async def cancel_any_state(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    await owner.ui.cancel_state(state=state, query=query)


if Tipbot.MAINTENANCE:
    # /------ MAINTENANCE HANDLE ------\ #
    @dp.message_handler(lambda message: message.text.startswith(('tip', 'Tip')))
    @dp.message_handler(commands=['details, tip', 'Tip', 'start', 'help', 'faq', 'wallet'])
    async def maintenance(message: types.Message):
        owner = TipBotUser.from_obj(message.from_user)
        await owner.ui.maintenance(message)


# /------ CREATE ACCOUNT ALIAS HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['new_alias'])
async def create_account_alias(message: types.Message):
    if len(message.text.split(' ')) > 2 and \
        message.text.split(' ')[1].startswith('#'):
        owner = TipBotUser.from_obj(message.from_user)
        await owner.ui.register_alias(message=message)


# /------ GET ACCOUNT ALIAS DETAILS ------\ #
@dp.message_handler(commands=COMMANDS['alias_details'])
async def get_alias_details(message: types.Message):
    if len(message.text.split(' ')) > 1 and message.text.split(' ')[1].startswith('#'):
        owner = TipBotUser.from_obj(message.from_user)

        if owner.wallet:
            await owner.ui.alias_details(message=message)


# TODO: UPDATE OR REMOVE ALIAS
# /------ GET ACCOUNT ALIAS DETAILS ------\ #
@dp.message_handler(commands=COMMANDS['alias_details'])
async def get_alias_details(message: types.Message):
    if len(message.text.split(' ')) > 1 and message.text.split(' ')[1].startswith('#'):
        owner = TipBotUser.from_obj(message.from_user)

        if owner.wallet:
            await owner.ui.alias_details(message=message)


@dp.message_handler(commands=['spam_message'], state='*')
async def spam_message(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.spam_message(message)

"""=================================================="""

# TODO: TEST  /------ WALLET GUI UPDATE ------\ #
@dp.message_handler(commands=['update_balance'], state='*')
async def wallet(message: types.Message, state: FSMContext):
    owner = TipBotUser.from_obj(message.from_user)

    if owner.wallet:
        owner.wallet.update_balance()


# TODO:  /------ TESTING ------\ #
@dp.message_handler(commands=['msg'], state='*')
async def tests(message: types.Message, state: FSMContext):
    # print(message.entities)
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.spam_message(message)

# /------ START MAIN LOOP ------\ #
if __name__ == '__main__':
    logger.info("starting")
    executor.start_polling(dp, skip_updates=True)