import hashlib

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, \
    InputTextMessageContent
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from decimal import Decimal
from aiogram import *

import requests
import json
import time

from settings import Database, Tipbot, MarketData
import long_strings as strings
from logger_ import logger
from keys import TOKEN
import tools


__version__ = '1.0'

# /------ AIOGRAM BOT SETTINGS ------\ #
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=tools.temp_storage())

DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL
PRICE = MarketData()
COMMANDS = tools.COMMANDS

# Wallet GUI buttons callback
wallet_cb = CallbackData('wallet', 'action', 'user', 'username')
donate_cb = CallbackData('donate', 'action', 'amount')


# Manage Wallet GUI states
class WithdrawStates(StatesGroup):
    ask_for_address = State()
    ask_for_amount = State()
    confirmation = State()

class SendStates(StatesGroup):
    ask_for_recipient = State()
    ask_for_amount = State()
    confirmation = State()

class DonateStates(StatesGroup):
    ask_for_amount = State()
    amount_from_button = State()
    confirmation = State()


# //-- BALANCE INLINE -- \\ #
@dp.inline_handler(lambda inline_query: 'wallet' in inline_query.query)
async def inline_welcome(inline_query: InlineQuery):
    query = 'balance'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    user = inline_query['from'].__dict__['_values']
    result_id: str = hashlib.md5(inline_query.query.encode()).hexdigest()
    thumb_url = "https://i.ibb.co/ypTVqvY/photo-2022-03-31-21-04-19.jpg"
    title = "EPIC Tip-Bot Wallet"
    bot_name = await bot.get_me()

    response = requests.post(url=full_url, data=json.dumps(user))

    if response.status_code == 200:
        response = json.loads(response.content)

        if response['error']:
            lines = ['Please setup your account and wallet', f"Talk to @{bot_name.username}"]
        else:
            if 'EPIC' in response['data'].keys():
                epic_balance = response['data']['EPIC']
            else:
                epic_balance = 0.0

            lines = [f"Balance: {epic_balance} EPIC"]

        item = InlineQueryResultArticle(
            id=result_id,
            title=title,
            description='\n'.join(lines),
            thumb_url=thumb_url,
            input_message_content=InputTextMessageContent(f'Manage your wallet: @{bot_name.username}', parse_mode=ParseMode.HTML)
            )
        await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


# // -- TIP INLINE -- \\ #
@dp.inline_handler(lambda inline_query: 'tip' in inline_query.query)
async def inline_welcome(inline_query: InlineQuery):
    """
    User can type in any chat window `tip @username amount` and click
    InlineQueryResult to send as ready /tip command
    """
    result_id: str = hashlib.md5(inline_query.query.encode()).hexdigest()
    thumb_url = "https://i.ibb.co/ypTVqvY/photo-2022-03-31-21-04-19.jpg"
    title = "Send Epic-Cash TIP"
    lines = [f"type @username and amount",
             "and click here"]

    item = InlineQueryResultArticle(
        id=result_id,
        title=title,
        description='\n'.join(lines),
        thumb_url=thumb_url,
        input_message_content=InputTextMessageContent(inline_query.query, parse_mode=ParseMode.HTML)
        )
    await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


# /------ CREATE ACCOUNT HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['create'])
async def create(message: types.Message):
    query = 'users/create'
    full_url = f'{DJANGO_API_URL}/{query}/'
    private_chat = message.from_user.id
    user, message_ = tools.parse_user_and_message(message)

    response = requests.post(url=full_url, data=json.dumps(user))
    response = json.loads(response.content)

    if not response['error']:
        msg = f"✅ Account created successfully!\n\n" \
              f"▪️️ [WALLET SEEDPHRASE AND PASSWORD]({response['data']})\n\n" \
              f"▪️️ Please backup message from link ️\n" \
              f"▪️️ Open your wallet 👉 /wallet" \

    else:
        if 'account already active' in response['msg']:
            msg = f"🟢 Your account is already active :)"
        else:
            msg = f"🟡 {response['msg']}"

    await send_message(text=msg, chat_id=private_chat)


# /------ WALLET GUI HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['wallet'], state='*')
async def wallet(message: types.Message, state: FSMContext):
    query = 'balance'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    private_chat = message.from_user.id
    user, _ = tools.parse_user_and_message(message)

    # Reset old state and data
    await state.finish()
    await state.reset_data()

    # Prepare main wallet inline keyboard
    keyboard = tools.build_wallet_keyboard(user, wallet_cb)

    # Display loading wallet GUI
    wallet_gui = await send_message(
        text=strings.loading_wallet_1(), chat_id=private_chat, reply_markup=keyboard)

    # Get Epic-Cash price in USD from Coingecko API
    epic_vs_usd = PRICE.price_epic_vs('USD')

    # Save user dict to temp storage
    await state.update_data(active_user=user)

    # Send POST request to get wallet balance from network
    try:
        response = requests.post(url=full_url, data=json.dumps(user))
    except requests.exceptions.ConnectionError:
        # Update loading wallet GUI to error wallet
        await wallet_gui.edit_text(text=strings.connection_error_wallet(),
                                   reply_markup=keyboard,
                                   parse_mode=ParseMode.MARKDOWN)
        return

    # Serialize POST request response
    response = json.loads(response.content)

    # Handle response error
    if response['error']:
        if 'Connection problems' in response['msg']:
            text = strings.connection_error_wallet()
        else:
            text = strings.invalid_wallet()

        # Update loading wallet GUI to error wallet
        await wallet_gui.edit_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        return

    # Handle case when wallet needs to update new transactions
    status = response['msg']
    while 'Updating' in status:
        await wallet_gui.edit_text(text=strings.loading_wallet_2(),
                                   reply_markup=keyboard,
                                   parse_mode=ParseMode.MARKDOWN)
        response = requests.post(url=full_url, data=json.dumps(user))
        response = json.loads(response.content)
        status = response['msg']
        time.sleep(0.3)
        await wallet_gui.edit_text(text=strings.loading_wallet_1(),
                                   reply_markup=keyboard,
                                   parse_mode=ParseMode.MARKDOWN)
        time.sleep(0.3)

    # Prepare updated GUI string
    if 'EPIC' in response['data'].keys():
        epic_balance = response['data']['EPIC']
    else:
        epic_balance = 0.0

    balance_in_usd = f"{round(Decimal(epic_balance) * epic_vs_usd, 2)} USD" if epic_vs_usd else ''
    wallet_gui_string = strings.ready_wallet(epic_balance, balance_in_usd)

    # Save epic_balance to temp storage
    await state.update_data(epic_balance=epic_balance)

    # Update loading wallet GUI to ready wallet
    await wallet_gui.edit_text(text=wallet_gui_string,
                               reply_markup=keyboard,
                               parse_mode=ParseMode.MARKDOWN)


# /------ WALLET GUI DEPOSIT ADDRESS STEP 1/1 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='deposit'), state='*')
async def gui_deposit(query: types.CallbackQuery, callback_data: dict):
    user = {'id': callback_data['user'], 'username': callback_data['username']}
    await address(query.message, custom_user=user)
    await query.answer()


# /------ WALLET GUI WITHDRAW STEP 1/3 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='withdraw'), state='*')
async def gui_withdraw(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    # Set new state
    await WithdrawStates.ask_for_address.set()

    # Ask user for address
    ask_for_address = await query.message.reply(text='📩 Please send me address to withdraw:',
                                                reply=False, reply_markup=tools.cancel_keyboard())
    # Save message to remove to temp storage
    await state.update_data(msg_ask_for_address=ask_for_address)
    await query.answer()


# /------ WALLET GUI WITHDRAW STEP 2/3 ------\ #
@dp.message_handler(state=WithdrawStates.ask_for_address)
async def handle_withdraw_address(message: types.Message, state: FSMContext):
    private_chat = message.from_user.id
    withdraw_address = message.text.strip()

    # Validate withdraw address and save to storage
    if tools.is_valid_address(withdraw_address):
        await state.update_data(address=withdraw_address)

        # Remove messages from previous state
        await tools.remove_state_messages(state)

        # Set new state
        await WithdrawStates.ask_for_amount.set()

        # Send message about amount
        ask_for_amount = await send_message(text='💵 How much to withdraw?',
                                            chat_id=private_chat,
                                            reply_markup=tools.cancel_keyboard())
    else:
        # Remove messages from previous state
        await tools.remove_state_messages(state)

        # Send invalid amount message
        ask_for_amount = await send_message(text='🔸 Invalid withdraw address, try again:',
                                            chat_id=private_chat,
                                            reply_markup=tools.cancel_keyboard())

    # Save message to remove to temp storage
    await state.update_data(msg_ask_for_amount=ask_for_amount)


# /------ WALLET GUI WITHDRAW STEP 3/3 ------\ #
@dp.message_handler(state=WithdrawStates.ask_for_amount)
async def handle_withdraw_amount(message: types.Message, state: FSMContext):
    private_chat = message.from_user.id
    amount = message.text.strip()

    try:
        # Validate and save amount
        amount = float(amount)
        await state.update_data(amount=amount)

        # Remove messages from previous state
        await tools.remove_state_messages(state)

        # Set new state
        await WithdrawStates.confirmation.set()
        data = await state.get_data()

        confirmation_string = f" ☑️ Confirm your withdraw request:\n\n" \
                              f"`▪️ Withdraw {data['amount']} EPIC to:`\n" \
                              f"`{data['address']}`\n"

        confirmation_keyboard = InlineKeyboardMarkup(one_time_keyboard=True)

        confirmation_keyboard.row(
            InlineKeyboardButton(text=f'✅ Confirm', callback_data='confirm_withdraw'),
            InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
            )

        # Send confirmation keyboard
        confirmation = await send_message(text=confirmation_string,
                                          chat_id=private_chat,
                                          reply_markup=confirmation_keyboard)

        # Save message to remove to temp storage
        await state.update_data(msg_confirmation=confirmation)

    except Exception as e:
        # Remove messages from previous state
        await tools.remove_state_messages(state)
        logger.error(e)

        # Send wrong amount message
        confirmation = await send_message(text='🔸 Wrong amount, try again', chat_id=private_chat)

        # Save message to remove to temp storage
        await state.update_data(msg_confirmation=confirmation)


# /------ WALLET GUI SEND STEP 1/3 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='send'), state='*')
async def gui_send(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    # Set new state
    await SendStates.ask_for_recipient.set()

    # Ask user for recipient
    ask_for_recipient = await query.message.reply(text='📩 Provide receiver @username',
                                                  reply=False, reply_markup=tools.cancel_keyboard())
    # Save message to remove to temp storage
    await state.update_data(msg_ask_for_recipient=ask_for_recipient)
    await query.answer()


# /------ WALLET GUI SEND STEP 2/3 ------\ #
@dp.message_handler(state=SendStates.ask_for_recipient)
async def handle_send_recipient(message: types.Message, state: FSMContext):
    private_chat = message.from_user.id

    # Validate recipient and save to storage
    if message.entities:
        recipient = message.parse_entities().replace('@', '')
        await state.update_data(recipient={'username': recipient})

        # Remove messages from previous state
        await tools.remove_state_messages(state)

        # Set new state
        await SendStates.ask_for_amount.set()

        # Send message about amount
        ask_for_amount = await send_message(text='💵 How much to send?',
                                            chat_id=private_chat,
                                            reply_markup=tools.cancel_keyboard())
    else:
        # Remove messages from previous state
        await tools.remove_state_messages(state)

        # Send invalid amount message
        ask_for_amount = await send_message(text='🔸 Invalid recipient username, try again:',
                                            chat_id=private_chat,
                                            reply_markup=tools.cancel_keyboard())

    # Save message to remove to temp storage
    await state.update_data(msg_ask_for_amount=ask_for_amount)


# /------ WALLET GUI SEND STEP 3/3 ------\ #
@dp.message_handler(state=SendStates.ask_for_amount)
async def handle_send_amount(message: types.Message, state: FSMContext):
    private_chat = message.from_user.id
    amount = message.text.strip()

    try:
        # Validate and save amount
        amount = float(amount)
        await state.update_data(amount=amount)

        # Remove messages from previous state
        await tools.remove_state_messages(state)

        # Set new state
        await SendStates.confirmation.set()
        data = await state.get_data()

        confirmation_string = f" ☑️ Confirm your send request:\n\n" \
                              f"`▪️ Send {data['amount']} EPIC to` " \
                              f"`@{data['recipient']['username']}`\n"

        confirmation_keyboard = InlineKeyboardMarkup(one_time_keyboard=True)

        confirmation_keyboard.row(
            InlineKeyboardButton(text=f'✅ Confirm', callback_data='confirm_send'),
            InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
            )

        # Send confirmation keyboard
        confirmation = await send_message(text=confirmation_string,
                                          chat_id=private_chat,
                                          reply_markup=confirmation_keyboard)

        # Save message to remove to temp storage
        await state.update_data(msg_confirmation=confirmation)

    except Exception as e:
        # Remove messages from previous state
        await tools.remove_state_messages(state)
        logger.error(e)

        # Send wrong amount message
        confirmation = await send_message(text='🔸 Wrong amount, try again', chat_id=private_chat)

        # Save message to remove to temp storage
        await state.update_data(msg_confirmation=confirmation)


# /------ WALLET GUI DONATE STEP 1/2 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='donate'), state='*')
async def gui_donate(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    private_chat = callback_data['user']

    # Set new state
    await DonateStates.ask_for_amount.set()

    # Send message about amount
    ask_for_amount = await send_message(text='💵 How much donate to developer?',
                                        chat_id=private_chat,
                                        reply_markup=tools.donate_keyboard())
    # Save message to remove to temp storage
    await state.update_data(msg_ask_for_amount=ask_for_amount)
    await query.answer()


# /------ WALLET GUI DONATE STEP 2/2 ------\ #
@dp.callback_query_handler(text=['donate_1', 'donate_5', 'donate_10'],
                           state=DonateStates.ask_for_amount)
async def handle_donate_amount(query: types.CallbackQuery, state: FSMContext):
    # Parse and save amount
    amount = float(query.data.split('_')[1])
    await state.update_data(amount=amount)

    # Remove messages from previous state
    await tools.remove_state_messages(state)

    # Set new state and provide donation address
    await SendStates.confirmation.set()
    await state.update_data(address=Tipbot.DONATION_ADDRESS)

    data = await state.get_data()
    private_chat = data['active_user']['id']

    # Prepare confirmation string and keyboard
    confirmation_string = f" ☑️ Confirm your donation:\n\n" \
                          f"`▪️ Send {data['amount']} EPIC to developer`"

    confirmation_keyboard = InlineKeyboardMarkup(one_time_keyboard=True)
    confirmation_keyboard.row(
        InlineKeyboardButton(text=f'✅ Confirm', callback_data='confirm_send'),
        InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
        )

    # Send confirmation keyboard
    confirmation = await send_message(text=confirmation_string,
                                      chat_id=private_chat,
                                      reply_markup=confirmation_keyboard)

    # Save message to remove to temp storage
    await state.update_data(msg_confirmation=confirmation)


# /------ WALLET GUI SUPPORT STEP 1/1 ------\ #
@dp.callback_query_handler(wallet_cb.filter(action='support'), state='*')
async def gui_support(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    private_chat = callback_data['user']
    support_link = f"[@blacktyg3r](https://t.me/blacktyg3r)"
    msg = f'🔘 Need help? Talk to {support_link}'

    await send_message(text=msg, chat_id=private_chat)
    await query.answer()


# /------ WALLET GUI SEND EPIC CALLBACK ------\ #
@dp.callback_query_handler(text=['confirm_withdraw', 'confirm_send'],
                           state=[WithdrawStates.confirmation, SendStates.confirmation])
async def handle_send_epic(query: types.CallbackQuery, state: FSMContext):
    api_query = 'send_transaction'
    full_url = f'{TIPBOT_API_URL}/{api_query}/'
    data = await state.get_data()
    private_chat = data['active_user']['id'] if 'active_user' in data.keys() else None

    # TODO: Better handle for no active_user case
    if not private_chat:
        return

    # Build and send withdraw transaction
    request_data = {
        'sender': data['active_user'],
        'receiver': data['recipient'] if 'recipient' in data.keys() else {'username': None},
        'address': data['address'] if 'address' in data.keys() else None,
        'amount': data['amount']
        }

    response = requests.post(url=full_url, data=json.dumps(request_data))

    if response.status_code != 200:
        msg = f"🔴 Transaction send error"
        await send_message(text=msg, chat_id=private_chat)
        return

    response = json.loads(response.content)

    if response['error']:
        if 'no account' in response['msg']:
            msg = f"🟡 @{data['recipient']['username']} have no Tip-Bot account yet."
        elif 'sendBlock.Height must be larger than 1' in response['msg']:
            msg = f"🟡 Insufficient balance."
        else:
            msg = f"🟡 {response['msg']}"

        await send_message(text=msg, chat_id=private_chat)
        await tools.remove_state_messages(state)
        await query.answer()
        return

    # Show user notification/alert
    await query.answer(text='Transaction Confirmed!')
    time.sleep(1)

    # Remove messages from previous state
    await tools.remove_state_messages(state)

    amount = tools.float_to_str(data['amount'])
    sender = f"*@{request_data['sender']['username']}*"

    # Create Vitescan.io explorer link to transaction
    transaction_hash = response['data']['transaction']['data']['hash']
    explorer_url = tools.vitescan_tx_url(transaction_hash)

    # Prepare user confirmation message
    private_msg = f"✅ Transaction sent successfully\n" \
                  f"▪️ [Transaction details (vitescan.io)]({explorer_url})"
    receiver_msg = f"💸   `{amount} EPIC from`   {sender}"

    # Send tx confirmation to sender's private chat
    await send_message(text=private_msg, chat_id=private_chat)

    # Send notification to receiver's private chat
    if 'receiver' in response['data'].keys():
        await send_message(text=receiver_msg, chat_id=response['data']['receiver']['id'])

    # Finish withdraw state
    await state.finish()
    await query.answer()


# /------ START/HELP HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['start'])
async def start(message: types.Message):
    private_chat = message.from_user.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.HELP_STRING, parse_mode=ParseMode.MARKDOWN)
    await bot.send_media_group(chat_id=private_chat, media=media)


# /------ FAQ HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['faq'])
async def start(message: types.Message):
    private_chat = message.from_user.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.FAQ_STRING, parse_mode=ParseMode.MARKDOWN)
    await bot.send_media_group(chat_id=private_chat, media=media)


# /------ DISPLAY DEPOSIT ADDRESS HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['address'])
async def address(message: types.Message, custom_user=None):
    query = 'address'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    active_chat = message.chat.id

    # We can pass custom user_id to fetch address
    # from user different from sender itself
    if not custom_user:
        user, message_ = tools.parse_user_and_message(message)
    else:
        user = custom_user

    response = requests.post(url=full_url, data=json.dumps(user))
    response = json.loads(response.content)

    if not response['error']:
        msg = f"🏷  *Your Deposit Address:*\n" \
              f"`{response['data']}`\n\n" \
              f"👤  *Your username:*\n" \
              f"`@{user['username']}`"
    else:
        msg = f"🔴 {response['msg']}"

    await send_message(text=msg, chat_id=active_chat)


# /------ DISPLAY BALANCE HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['balance'])
async def balance(message: types.Message):
    query = 'balance'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    private_chat = message.from_user.id
    user, message_ = tools.parse_user_and_message(message)

    response = requests.post(url=full_url, data=json.dumps(user))
    response = json.loads(response.content)

    if not response['error']:
        status = response['msg']

        if 'Updating' in status:
            msg = f"▫️ {response['data']}"
            reply = await message.reply(msg, reply=False, parse_mode=ParseMode.MARKDOWN)

            while 'Updating' in status:
                time.sleep(0.7)
                await reply.edit_text(f"◾️ {response['data']}")
                time.sleep(0.7)
                await reply.edit_text(f"▫️ {response['data']}")
                response = requests.post(url=full_url, data=json.dumps(user))
                response = json.loads(response.content)
                status = response['msg']

            await reply.delete()

        balances = []

        for symbol, value in response['data'].items():
            balances.append(f"`{value} {symbol}`")

        balances_str = '\n'.join(balances)
        msg = f"🪙 *Wallet Balance:*\n {balances_str}"
    else:
        msg = f"🔴 {response['msg']}"

    await send_message(text=msg, chat_id=private_chat)


# /------ SEND EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['send'], state='*')
async def send(message: types.Message):
    query = 'send_transaction'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    private_chat = message.from_user.id

    # Prepare and validate sending params
    data = tools.parse_send_command(message)

    if data['error']:
        return

    data = data['data']
    response = requests.post(url=full_url, data=json.dumps(data))

    if response.status_code != 200:
        msg = f"🔴 Transaction send error"
        await send_message(text=msg, chat_id=private_chat)
        return

    response = json.loads(response.content)

    if response['error']:
        msg = f"🟡 {response['msg']}"
        await send_message(text=msg, chat_id=private_chat)
        return

    amount = tools.float_to_str(data['amount'])
    sender = f"*@{data['sender']['username']}*"

    # Create Vitescan.io explorer link to transaction
    transaction_hash = response['data']['transaction']['data']['hash']
    explorer_url = tools.vitescan_tx_url(transaction_hash)

    # Prepare receiver or address
    if data['receiver']['username']:
        receiver_mention = f"*@{data['receiver']}*"
    else:
        receiver_mention = f"`{data['address']}`"

    # Prepare user confirmation message
    private_msg = f"✅ {amount} EPIC to {receiver_mention} " \
                  f"▫️ [Transaction details (vitescan.io)]({explorer_url})"
    receiver_msg = f"{amount} EPIC from {sender}"

    # Send tx confirmation to sender's private chat
    await send_message(text=private_msg, chat_id=private_chat)

    # Send notification to receiver's private chat
    if 'receiver' in response['data'].keys():
        await send_message(text=receiver_msg, chat_id=response['data']['receiver']['id'])


# /------ DONATION EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['donation'])
async def donation(message: types.Message):
    query = 'send_transaction'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    private_chat = message.from_user.id
    data = tools.parse_donation_command(message)

    if not data['error']:
        # Add Vite wallet for donations
        data['data']['address'] = Tipbot.DONATION_ADDRESS

        response = requests.post(url=full_url, data=json.dumps(data['data']))

        if response.status_code == 200:
            response = json.loads(response.content)

            if not response['error']:
                explorer_url = tools.vitescan_tx_url(response['data']['transaction']['data']['hash'])
                private_msg = f"✅ Donation of {tools.float_to_str(data['data']['amount'])} EPIC\n" \
                              f"▫️ [Donation details]({explorer_url})"
                await send_message(text=private_msg, chat_id=private_chat)

            else:
                if 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"🔴 Your wallet is empty."
                else:
                    msg = f"🔴 {response['msg']}"
                await send_message(text=msg, chat_id=private_chat)
        else:
            logger.error(response.status_code)
            msg = f"🔴 Donation send error"
            await send_message(text=msg, chat_id=private_chat)

    else:
        logger.error(data['msg'])
        msg = f"🔴 {data['msg']}"
        await send_message(text=msg, chat_id=private_chat)


# /------ TIP EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['tip'])
@dp.message_handler(lambda message: message.text.startswith('tip'))
async def tip(message: types.Message):
    query = 'send_transaction'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    active_chat = message.chat.id
    private_chat = message.from_user.id

    data = tools.parse_tip_command(message)

    # Prepare and validate sending params
    if not data['error']:
        response = requests.post(url=full_url, data=json.dumps(data['data']))

        if response.status_code == 200:
            response = json.loads(response.content)

            if not response['error']:
                explorer_url = tools.vitescan_tx_url(response['data']['transaction']['data']['hash'])
                receiver = data['data']['receiver']['username']
                private_msg = f"✅ {tools.float_to_str(data['data']['amount'])} EPIC to *@{receiver}*\n" \
                              f"▫️ [Tip details]({explorer_url})"
                public_msg = f"❤️ *@{data['data']['sender']['username']} {tools.float_to_str(data['data']['amount'])} TIP to @{data['data']['receiver']['username']}*"
                receiver_msg = f"💸 {tools.float_to_str(data['data']['amount'])} EPIC from *@{data['data']['sender']['username']}*"

                # Send tx confirmation to sender's private chat
                if not response['data']['receiver']['is_bot']:
                    await send_message(text=private_msg, chat_id=private_chat)

                # Send notification to receiver's private chat
                if 'receiver' in response['data'].keys():
                    if not response['data']['receiver']['is_bot']:
                        await send_message(text=receiver_msg, chat_id=response['data']['receiver']['id'])

                # Replace original /tip user message with tip confirmation in active channel
                await send_message(text=public_msg, chat_id=active_chat)
            else:
                if 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"🔴 Your wallet is empty."
                else:
                    msg = f"🔴 {response['msg']}"
                await send_message(text=msg, chat_id=private_chat)
        else:
            msg = f"🔴 Tip send error"
            await send_message(text=msg, chat_id=private_chat)

    else:
        logger.error(data['msg'])
        msg = f"🔴 {data['msg']}"
        await send_message(text=msg, chat_id=private_chat)

    await message.delete()


async def send_message(**kwargs):
    """Helper function for sending messages from bot to TelegramUser"""
    message = await bot.send_message(
        **kwargs, parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
        )
    return message


@dp.callback_query_handler(text='cancel_any', state='*')
async def cancel_any_state(query: types.CallbackQuery, state: FSMContext):
    # Remove messages
    await tools.remove_state_messages(state)

    # Clean temp storage except active_user
    data = await state.get_data()

    if 'active_user' in data.keys():
        user = data['active_user']
        await state.reset_data()
        await state.update_data(active_user=user)
    else:
        await state.reset_data()

    # Reset state
    logger.info(f"Reset state")
    await state.finish()
    await query.answer()


# TODO: History Handle
# # /------ DISPLAY TX HISTORY HANDLE ------\ #
# @dp.message_handler(commands=COMMANDS['history'])
# async def history(message: types.Message):
#     user_query = 'users'
#     tx_query = 'transactions'
#     private_chat = message.from_user.id
#     user, message_ = tools.parse_user_and_message(message)
#
#     # Get UserTelegram Wallet instance to get transaction history
#     user = requests.get(url=f'{DJANGO_API_URL}/{user_query}/', params={'user_id': user['id']}).json()
#     user_wallet_address = user[0]['wallet'][0]
#
#     # Get transactions for that Wallet
#     transactions = requests.get(url=f'{DJANGO_API_URL}/{tx_query}/', params={'address': user_wallet_address})
#     transactions = json.loads(transactions.content)
#
#     # Sort transactions
#     received = [tx for tx in transactions if user_wallet_address in tx['address']]
#     send = [tx for tx in transactions if user_wallet_address in tx['sender']]
#
#     if not response['error']:
#         msg = f"📄  *Transactions History:*\n" \
#               f"`{response['data']}`\n"
#     else:
#         msg = f"🔴 {response['msg']}"
#
#     await send_message(text=msg, chat_id=private_chat)


# /------ START MAIN LOOP ------\ #
if __name__ == '__main__':
    logger.info("starting")
    executor.start_polling(dp, skip_updates=True)
