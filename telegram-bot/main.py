from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
from aiogram import *

from random import randint
import requests
import json
import time

from settings import Database, Tipbot
from logger_ import logger
from keys import TOKEN
import tools


__version__ = '1.0'

# /------ AIOGRAM BOT SETTINGS ------\ #
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)

DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL
COMMANDS = {'start': ['start', 'help', 'help@epic_vitex_bot', 'help@EpicTipBot'],
            'create': ['create', 'register'],
            'balance': ['balance', 'bal', ],
            'address': ['address', 'deposit', ],
            'history': ['history', 'transactions', ],
            'send': ['send', 'withdraw', ],
            'cancel': ['cancel'],
            'donation': ['donation', ],
            'tip': ['tip', ],
            # GUI / Keyboards / includes
            'wallet': ['wallet', ]
            }


@dp.message_handler(commands=COMMANDS['wallet'])
async def wallet(message: types.Message):
    private_chat = message.from_user.id

    await message.reply_media_group(media=media, reply=False)
    await send_message(text="Epic-Cash TipBot Wallet", chat_id=private_chat,
                       reply_markup=keyboard_inline)


button1 = InlineKeyboardButton(text="👋 Deposit", callback_data="randomvalue_of10")
button2 = InlineKeyboardButton(text="💋 Withdraw", callback_data="randomvalue_of100")
keyboard_inline = InlineKeyboardMarkup().add(button1, button2)


@dp.callback_query_handler(text=["randomvalue_of10", "randomvalue_of100"])
async def random_value(call: types.CallbackQuery):
    private_chat = call.message.from_user.id

    if call.data == "randomvalue_of10":
        await call.message.answer(randint(1, 10))
    if call.data == "randomvalue_of100":
        await call.message.answer(randint(1, 100))
    await call.answer()


async def send_message(**kwargs):
    """Helper function for sending messages from bot to TelegramUser"""
    await bot.send_message(
        **kwargs, parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
        )


# /------ START/HELP HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['start'])
async def start(message: types.Message):
    private_chat = message.from_user.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.HELP_STRING, parse_mode=ParseMode.MARKDOWN)
    await bot.send_media_group(chat_id=private_chat, media=media)


# /------ CREATE ACCOUNT HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['create'])
async def create(message: types.Message):
    query = 'users/create'
    full_url = f'{DJANGO_API_URL}/{query}/'
    active_chat = message.chat.id
    private_chat = message.from_user.id
    user, message_ = tools.parse_user_and_message(message)

    response = requests.post(url=full_url, data=json.dumps(user))
    response = json.loads(response.content)

    if not response['error']:
        msg = f"✅ {response['msg']}\n\n"
        msg += f"⚠️ Please backup message from link ⚠️\n\n" \
               f"➡️ [ONE TIME SECRET LINK]({response['data']})\n"
    else:
        msg = f"🟡 {response['msg']}"

    await send_message(text=msg, chat_id=private_chat)


# /------ DISPLAY DEPOSIT ADDRESS HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['address'])
async def address(message: types.Message):
    query = 'address'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    active_chat = message.chat.id
    private_chat = message.from_user.id
    user, message_ = tools.parse_user_and_message(message)

    response = requests.post(url=full_url, data=json.dumps(user))
    response = json.loads(response.content)

    if not response['error']:
        msg = f"🏷  *Tipbot Wallet Deposit Address:*\n" \
              f"`{response['data']}`\n"
    else:
        msg = f"🔴 {response['msg']}"

    await send_message(text=msg, chat_id=active_chat)


# /------ DISPLAY BALANCE HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['balance'])
async def balance(message: types.Message):
    query = 'balance'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    active_chat = message.chat.id
    private_chat = message.from_user.id
    user, message_ = tools.parse_user_and_message(message)

    response = requests.post(url=full_url, data=json.dumps(user))
    response = json.loads(response.content)
    print(response)

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
@dp.message_handler(commands=COMMANDS['send'])
async def send(message: types.Message):
    query = 'send_transaction'
    full_url = f'{TIPBOT_API_URL}/{query}/'
    active_chat = message.chat.id
    private_chat = message.from_user.id

    # Prepare and validate sending params
    data = tools.parse_send_command(message)

    if not data['error']:
        response = requests.post(url=full_url, data=json.dumps(data['data']))

        if response.status_code == 200:
            response = json.loads(response.content)

            # Parse API response
            if not response['error']:
                command = f"`({message.get_command(pure=True)} operation)`"
                explorer_url = tools.vitescan_tx_url(response['data']['transaction']['data']['hash'])
                receiver = f"@{data['data']['receiver']}" if data['data']['receiver']['username'] else data['data']['address']
                private_msg = f"✅ {tools.float_to_str(data['data']['amount'])} EPIC to *{receiver}* " \
                              f"{command if 'withdraw' in command else ''}\n" \
                              f"▫️ [Transaction details (vitescan.io)]({explorer_url})"
                receiver_msg = f"{data['data']['amount']} EPIC from *@{data['data']['sender']['username']}*"

                # Send tx confirmation to sender's private chat
                await send_message(text=private_msg, chat_id=private_chat)

                # Send notification to receiver's private chat
                if 'receiver' in response['data'].keys():
                    await send_message(text=receiver_msg, chat_id=response['data']['receiver']['id'])
            else:
                msg = f"🟡 {response['msg']}"
                await send_message(text=msg, chat_id=private_chat)
        else:
            # print(response.text)
            msg = f"🔴 Transaction send error"
            await send_message(text=msg, chat_id=private_chat)


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
            print(response.status_code)
            msg = f"🔴 Donation send error"
            await send_message(text=msg, chat_id=private_chat)

    else:
        print(data['msg'])
        msg = f"🔴 {data['msg']}"
        await send_message(text=msg, chat_id=private_chat)


# /------ TIP EPIC HANDLE ------\ #
@dp.message_handler(commands=COMMANDS['tip'])
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
                public_msg = f"❤️ *@{data['data']['sender']['username']} {tools.float_to_str(data['data']['amount'])} TIP @{data['data']['receiver']['username']}*"
                receiver_msg = f"💸 {tools.float_to_str(data['data']['amount'])} EPIC from *@{data['data']['sender']['username']}*"

                # Send tx confirmation to sender's private chat
                if not response['data']['receiver']['is_bot']:
                    await send_message(text=private_msg, chat_id=private_chat)

                # Send notification to receiver's private chat
                if 'receiver' in response['data'].keys():
                    if not response['data']['receiver']['is_bot']:
                        await send_message(text=receiver_msg, chat_id=response['data']['receiver']['id'])

                # Replace original /tip user message with tip confirmation in active channel
                await message.delete()
                await send_message(text=public_msg, chat_id=active_chat)
            else:
                if 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"🔴 Your wallet is empty."
                else:
                    msg = f"🔴 {response['msg']}"
                await send_message(text=msg, chat_id=private_chat)
        else:
            print(response.status_code)
            msg = f"🔴 Tip send error"
            await send_message(text=msg, chat_id=private_chat)

    else:
        print(data['msg'])
        msg = f"🔴 {data['msg']}"
        await send_message(text=msg, chat_id=private_chat)


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
