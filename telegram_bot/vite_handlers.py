from aiogram.dispatcher import FSMContext
from aiogram import *

from src.commands import COMMANDS
from src.user import TipBotUser
from src.ui import *
from src import dp


# /------ WALLET VITE DEPOSIT STEP 2/2 ------\ #
@dp.callback_query_handler(text='deposit_vite', state='*')
async def vite_deposit(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    await owner.ui.show_vite_deposit(query=query, state=state)


# /------ WALLET GUI WITHDRAW EPIC FINALIZE CALLBACK ------\ #
@dp.callback_query_handler(text=['confirm_vite_withdraw'], state=[DonateStates.confirmation, WithdrawStates.withdraw])
async def handle_withdraw_final(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.message.chat.id)
    await owner.vite_wallet.withdraw(state=state, query=query)


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
    await owner.vite_wallet.send_to_users(state=state, query=query)


# /------ WALLET GUI DONATE STEP 1/2 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='donate'), state='*')
async def gui_donate(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    await owner.ui.donate_1_of_2(state=state, query=query)


# /------ WALLET GUI DONATE STEP 2/2 ------\ #
@dp.callback_query_handler(text=['donate_1', 'donate_5', 'donate_10'], state=DonateStates.ask_for_amount)
async def handle_donate_amount(query: types.CallbackQuery, state: FSMContext):
    owner = TipBotUser(id=query.message.chat.id)
    await owner.ui.donate_2_of_2(state=state, query=query)


# /------ TIP EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['tip'])
@dp.message_handler(lambda message: message.text.startswith(('tip', 'Tip')) and 2 < len(message.text.split(' ')) < 10)
async def tip(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    if owner.is_registered:
        await owner.ui.send_tip_cmd(message=message)


# /------ CONFIRM FAILED TIP ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='confirm_failed_tip'), state='*')
async def confirm_failed_tip(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=query.from_user.id)
    if owner.id == int(callback_data['user']):
        await query.message.delete()


# /------ GET MNEMONICS HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['mnemonics'])
async def mnemonics(message: types.Message):
    owner = TipBotUser.from_obj(message.from_user)
    await owner.ui.show_mnemonics()


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

        if owner.vite_wallet:
            await owner.ui.alias_details(message=message)


# TODO: UPDATE OR REMOVE ALIAS
# /------ GET ACCOUNT ALIAS DETAILS ------\ #
@dp.message_handler(commands=COMMANDS['alias_details'])
async def get_alias_details(message: types.Message):
    if len(message.text.split(' ')) > 1 and message.text.split(' ')[1].startswith('#'):
        owner = TipBotUser.from_obj(message.from_user)

        if owner.vite_wallet:
            await owner.ui.alias_details(message=message)


# /------ WALLET GUI SUPPORT ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='support'), state='*')
async def gui_support(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    owner = TipBotUser(id=callback_data['user'])
    print(owner)
    await owner.ui.show_support(query=query)


# # TODO: TEST  /------ WALLET GUI UPDATE ------\ #
# @dp.message_handler(commands=['update_balance'], state='*')
# async def wallet(message: types.Message, state: FSMContext):
#     owner = TipBotUser.from_obj(message.from_user)
#     if owner.wallet:
#         owner.wallet.update_balance()
#
#
# # TODO:  /------ TESTING ------\ #
# @dp.message_handler(commands=['msg'], state='*')
# async def tests(message: types.Message, state: FSMContext):
#     # print(message.entities)
#     owner = TipBotUser.from_obj(message.from_user)
#     await owner.ui.spam_message(message)
