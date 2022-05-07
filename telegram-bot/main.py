from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, \
    InlineQueryResultArticle, InputTextMessageContent
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from aiogram import *

import requests
import random
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
    confirmation = State()


# /------ CREATE ACCOUNT HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['create'])
async def create(message: types.Message):
    # Create TipBotUser instance
    owner = tools.TipBotUser.from_obj(message.from_user)
    response = owner.register()

    # Handle error case
    if response['error']:
        logger.warning(f"{response['msg']}")

        if 'account already active' in response['msg']:
            msg = f"🟢 Your account is already active :)"
        else:
            msg = f"🟡 {response['msg']}"

    # Handle success creation
    else:
        msg = f"✅ Account created successfully!\n\n" \
              f"▪️️ [WALLET SEEDPHRASE AND PASSWORD]({response['data']})\n\n" \
              f"▪️️ Please backup message from link ️\n" \
              f"▪️️ Open your wallet 👉 /wallet"

    await send_message(text=msg, chat_id=owner.id)


# /------ WALLET GUI HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['wallet'], state='*')
async def wallet(message: types.Message, state: FSMContext):
    owner = tools.TipBotUser.from_obj(message.from_user)

    # Reset old state and data
    await state.reset_state(with_data=True)

    # Prepare main wallet GUI (message and inline keyboard)
    gui = tools.WalletGUI(user=owner, callback=wallet_cb)
    keyboard = gui.home_keyboard()

    # Display loading wallet GUI
    wallet_gui = await send_message(
        text=strings.loading_wallet_1(), chat_id=owner.id, reply_markup=keyboard)

    response = owner.wallet.epic_balance()

    # print(owner.wallet.cached_balance)

    # Handle response error
    if response['error']:
        if 'connection error' in response['msg']:
            text = strings.connection_error_wallet()
        else:
            text = strings.invalid_wallet()

        # Update loading wallet GUI to error wallet
        await wallet_gui.edit_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.error(f"{owner.username}: {response['msg']}")
        return

    # Handle case when wallet needs to update new transactions
    status = response['msg']

    while 'Updating' in status:
        await wallet_gui.edit_text(text=strings.loading_wallet_2(),
                                   reply_markup=keyboard,
                                   parse_mode=ParseMode.MARKDOWN)
        response = owner.wallet.epic_balance()
        status = response['msg']
        time.sleep(0.3)
        await wallet_gui.edit_text(text=strings.loading_wallet_1(),
                                   reply_markup=keyboard,
                                   parse_mode=ParseMode.MARKDOWN)
        time.sleep(0.3)

    # Prepare GUI strings
    epic_balance, balance_in_usd = response['data']['string']
    wallet_gui_string = strings.ready_wallet(epic_balance, balance_in_usd)

    # Update loading wallet GUI to ready wallet
    await wallet_gui.edit_text(text=wallet_gui_string,
                               reply_markup=keyboard,
                               parse_mode=ParseMode.MARKDOWN)

    logger.info(f"{owner.username}: wallet GUI loaded")


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
        amount = tools.float_to_str(data['amount'])

        confirmation_string = f" ☑️ Confirm your send request:\n\n" \
                              f"`▪️ Send {amount} EPIC to` " \
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
    private_chat = query.message.chat.id
    amount = float(query.data.split('_')[1])
    await state.update_data(amount=amount)

    # Remove messages from previous state
    await tools.remove_state_messages(state)

    # Set new state and provide donation address
    await SendStates.confirmation.set()
    await state.update_data(address=Tipbot.DONATION_ADDRESS)

    data = await state.get_data()
    amount = tools.float_to_str(data['amount'])

    # Prepare confirmation string and keyboard
    confirmation_string = f" ☑️ Confirm your donation:\n\n" \
                          f"`▪️ Send {amount} EPIC to developer`"

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
    sender = tools.TipBotUser(id=query.message.chat.id)
    private_chat = sender.id

    # Remove keyboard and display processing msg
    conf_msg = f"⏳ Processing transaction.."
    await data['msg_confirmation'].edit_text(text=conf_msg, reply_markup=None, parse_mode=ParseMode.MARKDOWN)

    # Build and send withdraw transaction
    request_data = {
        'sender': {'id': sender.id, 'username': sender.username},
        'receiver': data['recipient'] if 'recipient' in data.keys() else {'username': None},
        'address': data['address'] if 'address' in data.keys() else None,
        'amount': data['amount']
        }

    response = requests.post(url=full_url, data=json.dumps(request_data))

    if response.status_code != 200:
        msg = f"🔴 Transaction send error"
        logger.error(f"{sender.username}: Database connection error")
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

        logger.error(f"{sender.username}: {response['msg']}")
        await send_message(text=msg, chat_id=private_chat)
        await tools.remove_state_messages(state)
        await query.answer()
        return

    # Show user notification/alert
    await query.answer(text='Transaction Confirmed!')
    time.sleep(1)

    # Remove messages from previous state
    await tools.remove_state_messages(state)

    # Create Vitescan.io explorer link to transaction
    transaction_hash = response['data']['transaction']['data']['hash']
    explorer_url = tools.vitescan_tx_url(transaction_hash)

    # Prepare user confirmation message
    amount = tools.float_to_str(data['amount'])
    receiver = tools.TipBotUser(id=response['data']['receiver']['id']).username \
        if 'receiver' in response['data'].keys() else data['address']

    private_msg = f"✅ Transaction sent successfully\n" \
                  f"▪️️ [Transaction details (vitescan.io)]({explorer_url})"
    receiver_msg = f"💸 `{amount} EPIC from ` {sender.get_url()}"

    # Send tx confirmation to sender's private chat
    await send_message(text=private_msg, chat_id=private_chat)

    # Send notification to receiver's private chat
    if 'receiver' in response['data'].keys():
        await send_message(text=receiver_msg, chat_id=response['data']['receiver']['id'])

    # Finish withdraw state
    await state.finish()
    await query.answer()

    logger.info(f"{sender.username}: sent {amount} to {receiver}")


# /------ TIP EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['tip'])
@dp.message_handler(lambda message: message.text.startswith(('tip', 'Tip'))
                                    and 2 < len(message.text.split(' ')) < 10)
async def tip(message: types.Message):
    query = 'send_transaction'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    active_chat = message.chat.id
    private_chat = message.from_user.id
    max_receivers = 5

    data = tools.parse_tip_command(message)

    # Handle error when parsing user data from chat
    if data['error']:
        logger.error(data['msg'])
        msg = f"🔴 {data['msg']}"
        await send_message(text=msg, chat_id=private_chat)
        return

    # Handle case when tip command have wrong syntax
    if len(message.text.split(' ')) - len(data['data']['receiver']) != 2:
        logger.error('wrong tip command')
        return

    # Handle too many receivers:
    if len(data['data']['receiver']) > max_receivers:
        msg = f"Too many receivers: {len(data['data']['receiver'])}, max: {max_receivers}"
        logger.error(msg)
        await send_message(text=msg, chat_id=private_chat)
        await tools.delete_message(message)
        return

    # Iterate through list of receivers and send transaction for each
    for i, receiver in enumerate(data['data']['receiver']):

        if i > 0:
            # Respect anti-flood locking system
            time.sleep(2.2)

        copy = data['data']
        copy['receiver'] = receiver
        response = requests.post(url=full_url, data=json.dumps(copy))

        # Handle error with connection to database
        if response.status_code != 200:
            msg = f"🔴 Tip send error"
            logger.error(f"{data['sender']['username']}: tip send error: {response.status_code}")
            await send_message(text=msg, chat_id=private_chat)
            await tools.delete_message(message)
            return

        response = json.loads(response.content)

        # Handle error from VITE network
        if response['error']:
            if 'sendBlock.Height must be larger than 1' in response['msg']:
                msg = f"🔴 Your wallet is empty."
            else:
                msg = f"🔴 {response['msg']}"
            logger.error(f"{copy['sender']['username']}: {response['msg']}")
            await send_message(text=msg, chat_id=private_chat)
            await tools.delete_message(message)
            return

        # Handle success transaction
        explorer_url = tools.vitescan_tx_url(response['data']['transaction']['data']['hash'])
        receiver = tools.TipBotUser(response['data']['receiver']['id'])
        sender = tools.TipBotUser(copy['sender']['id'])
        amount = tools.float_to_str(copy['amount'])

        public_msg = f"❤️ {sender.get_url()} tipped `{amount} " \
                     f"EPIC` to {receiver.get_url()}"
        private_msg = f"✅ `{amount} EPIC` to {receiver.get_url()} \n" \
                      f"▪️️ [Tip details]({explorer_url})"
        receiver_msg = f"💸 `{amount} EPIC` from {sender.get_url()}"

        # Send tx confirmation to sender's private chat
        if not receiver.is_bot:
            await send_message(text=private_msg, chat_id=private_chat)

        # Send notification to receiver's private chat
        if not receiver.is_bot:
            await send_message(text=receiver_msg, chat_id=receiver.id)

        # Replace original /tip user message with tip confirmation in active channel
        await send_message(text=public_msg, chat_id=active_chat)

        logger.info(f"{sender.username}: sent {amount} to {receiver.username}")

    await tools.delete_message(message)


# //-- BLANK INLINE -- \\ #
@dp.inline_handler(lambda inline_query: (inline_query.query == '' or
                   inline_query.query) and len(inline_query.query.split(' ')) < 8)
async def inline_blank(inline_query: InlineQuery):
    user = inline_query['from'].__dict__['_values']

    # Check if user have already active account
    try:
        sender = tools.TipBotUser(id=user['id'])
    except Exception:
        await bot.answer_inline_query(inline_query.id, results=[],
                                      cache_time=1, is_personal=True,
                                      switch_pm_text='Create Tip-Bot Account Here',
                                      switch_pm_parameter='help')
        return

    response = sender.wallet.epic_balance()

    # Check if balance is positive
    if float(response['data']['string'][0]) < 0.00000001:
        switch_pm_text = "Deposit To Tip-Bot Wallet Here"
        switch_pm_parameter = 'deposit'

    else:
        switch_pm_text = f"Tip-Bot Balance: {response['data']['string'][0]} EPIC"
        switch_pm_parameter = 'start_wallet'

    items = []

    # Parse usernames or its parts to query and show result list
    if len(inline_query.query.split(' ')) > 0:

        # Parse username based on '@' if present
        if '@' in inline_query.query:
            match = inline_query.query.split('@')[-1].split(' ')[0]
            users = sender.query_users(num=10, match=match)

        # Try to search for possible variations, exclude potential amounts
        else:
            match = ''
            for match in inline_query.query.split(' '):
                try:
                    # if successful conversion ignore and continue
                    float(match)
                    continue
                except Exception:
                    # If conversion to float fails try to use is as part of username
                    break

            users = sender.query_users(num=10, match=match)
    else:
        # Get list of x random users to show as result list
        users = sender.get_users(num=5, random_=True)

    # Parse amount or set standard value for quick tips
    amount = 0
    for match in inline_query.query.split(' '):
        try:
            amount = float(match)
            break
        except Exception:
            continue

    amount = amount if amount else 0.01

    # Iterate users list and create result objects to display
    for user in users:
        id = f"{user['id'] * random.randint(1, 1000)}"
        title = f"➡️️ Quick Send {amount} EPIC to @{user['username']}"
        command = f"tip @{user['username']} {amount}"

        items.append(InlineQueryResultArticle(
            id=id,
            title=title,
            input_message_content=InputTextMessageContent(command, parse_mode=ParseMode.HTML)
            ))

    await bot.answer_inline_query(
        inline_query.id,
        results=items,
        cache_time=1, is_personal=True,
        switch_pm_text=switch_pm_text,
        switch_pm_parameter=switch_pm_parameter
        )


# //-- BALANCE INLINE -- \\ #
@dp.inline_handler(lambda inline_query: 'wallet' in inline_query.query)
async def inline_balance(inline_query: InlineQuery):
    user = inline_query['from'].__dict__['_values']
    thumb_url = "https://i.ibb.co/ypTVqvY/photo-2022-03-31-21-04-19.jpg"
    title = "EPIC Tip-Bot Wallet"
    sender = tools.TipBotUser(id=user['id'])
    response = sender.wallet.epic_balance()
    bot_name = await bot.get_me()

    if response['error']:
        lines = ['Please setup your account and wallet', f"Talk to @{bot_name.username}"]
    else:
        if 'EPIC' in response['data'].keys():
            epic_balance = tools.float_to_str(response['data']['EPIC'])
        else:
            epic_balance = 0.0

        lines = [f"Balance: {epic_balance} EPIC"]

    id = 123
    items = []
    for i, item in enumerate(range(1, 4)):
        items.append(InlineQueryResultArticle(
            id=f"{id + i}",
            title=title,
            description='\n'.join(lines),
            thumb_url=thumb_url,
            input_message_content=InputTextMessageContent(f'Manage your wallet: @{bot_name.username}',
                                                          parse_mode=ParseMode.HTML)
            ))
    await bot.answer_inline_query(inline_query.id, results=items, cache_time=1, is_personal=True)


# /------ START/HELP HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['start'])
async def start(message: types.Message):
    private_chat = message.from_user.id
    active_chat = message.chat.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.HELP_STRING, parse_mode=ParseMode.MARKDOWN)

    if Tipbot.ADMIN_ID in str(private_chat):
        await bot.send_media_group(chat_id=active_chat, media=media)
    else:
        await bot.send_media_group(chat_id=private_chat, media=media)


# /------ FAQ HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['faq'])
async def faq(message: types.Message):
    private_chat = message.from_user.id
    active_chat = message.chat.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.FAQ_STRING, parse_mode=ParseMode.MARKDOWN)

    if Tipbot.ADMIN_ID in str(private_chat):
        await bot.send_media_group(chat_id=active_chat, media=media)
    else:
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
        logger.info(f"{user['username']}: show deposit address")

    else:
        msg = f"🔴 {response['msg']}"
        logger.error(f"{user['username']}: {msg}")

    await send_message(text=msg, chat_id=active_chat)


# /------ DISPLAY BALANCE HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['balance'])
async def balance(message: types.Message):
    private_chat = message.from_user.id
    sender = tools.TipBotUser(id=message.from_user.id)
    response = sender.wallet.epic_balance()

    if response['error']:
        msg = f"🔴 {response['msg']}"
        logger.error(f"{sender.username}: {msg}")
        await send_message(text=msg, chat_id=private_chat)
        return

    status = response['msg']

    if 'Updating' in status:
        msg = f"▫️ {response['data']}"
        reply = await message.reply(msg, reply=False, parse_mode=ParseMode.MARKDOWN)

        while 'Updating' in status:
            time.sleep(0.7)
            await reply.edit_text(f"◾️ {response['data']}")
            time.sleep(0.7)
            await reply.edit_text(f"▫️ {response['data']}")
            response = sender.wallet.epic_balance()
            status = response['msg']

        await tools.delete_message(reply)

    balances = []

    for symbol, value in response['data'].items():
        balances.append(f"`{value} {symbol}`")

    balances_str = '\n'.join(balances)
    msg = f"🪙 *Wallet Balance:*\n {balances_str}"

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
        logger.error(f"{message.from_user.username}: {data}")
        return

    data = data['data']
    response = requests.post(url=full_url, data=json.dumps(data))

    if response.status_code != 200:
        msg = f"🔴 Transaction send error"
        logger.error(f"{message.from_user.username}: Transaction send error")
        await send_message(text=msg, chat_id=private_chat)
        return

    response = json.loads(response.content)

    if response['error']:
        msg = f"🟡 {response['msg']}"
        logger.error(f"{message.from_user.username}: {response['msg']}")
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

    logger.info(f"{message.from_user.username}: send success")


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


async def send_message(**kwargs):
    """Helper function for sending messages from bot to TelegramUser"""
    try:
        message = await bot.send_message(
            **kwargs, parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
            )
        return message
    except Exception as e:
        print(e)
        user = tools.TipBotUser(id=kwargs['chat_id'])
        name = user.username if user.username else user.id
        logger.error(f'SEND MSG ERROR: From {name}: "{kwargs["text"]}"')


@dp.callback_query_handler(text='cancel_any', state='*')
async def cancel_any_state(query: types.CallbackQuery, state: FSMContext):
    sender = tools.TipBotUser(id=query.from_user.id)

    # Remove messages
    await tools.remove_state_messages(state)

    # Reset state
    logger.info(f"{sender.username}: Reset state and data")
    await state.reset_state(with_data=True)
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
