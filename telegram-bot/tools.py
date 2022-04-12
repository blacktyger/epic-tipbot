from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import MessageToDeleteNotFound
from aiogram.contrib.fsm_storage.files import PickleStorage
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram import types
import requests

from typing import Union
import decimal
import json
import os

from logger_ import logger
from settings import Database, MarketData


ctx = decimal.Context()
PRICE = MarketData()
ctx.prec = 20
DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL


def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')


def get_amount(message: types.Message) -> Union[float, None]:
    """
    Parse amount from user's messages
    :param message: types.Message (AIOGRAM)
    :return: float or None
    """
    for match in message.text.split(' '):
        try:
            amount = float(match)
            return amount
        except Exception as e:
            continue

    return None


class TipBotWallet:
    """
    Deserialize Wallet JSON data from database and save as object.
    """
    def __init__(self,
                 address: str = None,
                 balance: dict = None
                 ):
        self.address = address
        self.balance = balance
        self.user = int

        if not self.address:
            logger.error(f'No address provided.')
            return

        # Prepare database query
        query = 'wallets'
        params = {'address': address}
        full_url = f'{DJANGO_API_URL}/{query}/'
        response = requests.get(url=full_url, params=params)

        if response.status_code != 200:
            logger.error(f'Wallet Database error: {response.status_code}')
            return

        response = json.loads(response.content)[0]

        for key, value in response.items():
            setattr(self, key, value)

    def epic_balance(self) -> dict:
        # Send POST request to get wallet balance from network
        query = 'balance'
        full_url = f'{TIPBOT_API_URL}/{query}/'
        request_data = {'id': self.user}

        try:
            response = requests.post(url=full_url, data=json.dumps(request_data))
        except requests.exceptions.ConnectionError:
            msg = f'{query} API call connection error.'
            logger.error(msg)
            return {'error': 1, 'msg': msg, 'data': None}

        if response.status_code != 200:
            msg = f'Wallet Database error: {response.status_code}'
            logger.error(msg)
            return {'error': 1, 'msg': msg, 'data': None}

        response = json.loads(response.content)

        if 'EPIC' in response['data'].keys():
            epic_balance = float_to_str(response['data']['EPIC'])
        else:
            epic_balance = 0.0

        # Get Epic-Cash price in USD from Coingecko API
        epic_vs_usd = PRICE.price_epic_vs('USD')
        balance_in_usd = f"{round(decimal.Decimal(epic_balance) * epic_vs_usd, 2)} USD" if epic_vs_usd else ''
        response['data']['string'] = epic_balance, balance_in_usd

        return response

    def __repr__(self):
        return f"TipBotWallet({self.address})"


class TipBotUser:
    """
    Deserialize TelegramUser JSON data from database and save as object.
    """
    def __init__(self,
                 id: Union[str, int] = None,
                 is_bot: bool = False,
                 wallet: TipBotWallet = None,
                 username: str = '',
                 first_name: str = None,
                 language_code: str = None):

        self.id = id
        self.is_bot = is_bot
        self.wallet = wallet
        self.username = username.lower()
        self.first_name = first_name
        self.language_code = language_code

        if not self.id and self.username:
            logger.error(f'No username and id, provide at least one.')
            return

        # Prepare database query
        query = 'users'
        params = {'user_id': self.id, 'username': self.username}
        full_url = f'{DJANGO_API_URL}/{query}/'
        response = requests.get(url=full_url, params=params)

        if response.status_code != 200:
            logger.error(f'TelegramUser Database error: {response.status_code}')
            return

        response = json.loads(response.content)[0]
        print(response)

        for key, value in response.items():
            if key == 'wallet':
                setattr(self, key, TipBotWallet(address=value[0]))
            else:
                setattr(self, key, value)

    def get_url(self):
        return f"[{self.username}](tg://user?id={self.id})"

def get_receiver(message: types.Message) -> Union[str, None]:
    """
    Parse receiver username from user's messages
    :param message: types.Message (AIOGRAM)
    :return: receiver string or None
    """
    if len(message.entities) > 0:
        for match in message.entities:
            if 'mention' in match['type']:
                start = match['offset']
                stop = start + match['length']
                return message.text[start:stop].replace('@', '').lower()
    else:
        try:
            return message.parse_entities().split(' ')[1].lower()
        except Exception as e:
            logger.error(f'Error parsing receiver {e}')

    return None


def get_address(message: types.Message) -> Union[str, None]:
    """
    Parse receiver vite address from user's messages
    :param message: types.Message (AIOGRAM)
    :return: receiver string or None
    """
    for match in message.text.split(' '):
        if is_valid_address(match):
            return match

    return None


def parse_user_and_message(message: types.Message) -> tuple:
    """Parse from User and Message instance to dict"""
    user = message.from_user.__dict__['_values']

    if 'username' not in user.keys():
        user['username'] = user['first_name']

    user['username'] = user['username'].lower()

    msg = {
        'id': message.message_id,
        'date': message.date.timestamp(),
        'text': message.text,
        'chat': message.chat.__dict__['_values'],
        'entities': message.entities,
        }

    return user, msg


def parse_donation_command(message: types.Message) -> dict:
    """Return data for developer donation transaction"""

    sender, _ = parse_user_and_message(message)
    amount = get_amount(message)

    if not amount:
        return {'error': 1, 'msg': 'Wrong amount value.', 'data': None}

    data = {
        'sender': sender,
        'receiver': None,
        'amount': amount,
        'address': None  # will be added after
        }
    response = {'error': 0, 'msg': 'Success', 'data': data}

    return response


def parse_tip_command(message: types.Message) -> dict:
    """Return data for TIP transaction"""
    sender, _ = parse_user_and_message(message)
    receiver = {'username': get_receiver(message)}
    amount = get_amount(message)

    print(receiver)

    if not receiver['username']:
        return {'error': 1, 'msg': 'Invalid recipient username.', 'data': None}

    if not amount:
        return {'error': 1, 'msg': 'Wrong amount value.', 'data': None}

    data = {
        'sender': sender,
        'receiver': receiver,
        'amount': amount,
        'address': None
        }

    return {'error': 0, 'msg': 'Success', 'data': data}


def parse_send_command(message: types.Message) -> dict:
    """Return data for send transaction"""
    amount = get_amount(message)
    address = get_address(message)
    receiver = {'username': get_receiver(message)}
    sender, _ = parse_user_and_message(message)

    logger.info(amount, sender['username'], '-->', receiver['username'], address)

    if not amount:
        return {'error': 1, 'msg': 'Wrong amount value.', 'data': None}

    if not receiver['username'] and not address:
        return {'error': 1, 'msg': 'Please provide `@username` or `vite Address`', 'data': None}

    data = {
        'sender': sender,
        'receiver': receiver,
        'address': address,
        'amount': amount
        }

    return {'error': 0, 'msg': 'Success', 'data': data}


def is_valid_address(address: str) -> bool:
    """Validate Vite address"""
    return len(address) == 55 and address.startswith('vite_')


def vitescan_tx_url(tx_hash):
    return f"https://vitescan.io/tx/{tx_hash}"


def build_wallet_keyboard(user: dict, callback: CallbackData) -> InlineKeyboardMarkup:
    """
    Prepare Wallet GUI InlineKeyboard
    :param callback: CallbackData instance (aiogram)
    :param user: TelegramUser dict
    :return: InlineKeyboardMarkup instance (aiogram)
    """

    buttons = ['deposit', 'withdraw', 'send', 'donate', 'support']
    icons = ['↘ ', '↗️ ', '➡️ ', '❤️ ', '💬️ ']

    buttons = [InlineKeyboardButton(
        text=f"{icons[i]}{btn.capitalize()}",
        callback_data=callback.new(action=btn, user=user['id'], username=user['username']))
        for i, btn in enumerate(buttons)]

    keyboard_inline = InlineKeyboardMarkup() \
        .row(buttons[0], buttons[1]) \
        .row(buttons[2], buttons[3]) \
        .add(buttons[4])

    return keyboard_inline


async def remove_state_messages(state: FSMContext):
    """Remove bot messages saved in temp storage"""
    if await state.get_state():
        data = await state.get_data()
        state_ = await state.get_state()

        # Remove messages
        if f'msg_{state_.split(":")[-1]}' in data.keys():
            try:
                logger.info('DELETE MSG: ', data[f'msg_{state_.split(":")[-1]}']['id'])
            except Exception:
                pass
            try:
                await data[f'msg_{state_.split(":")[-1]}'].delete()
            except MessageToDeleteNotFound:
                pass


def cancel_keyboard():
    """Initialize InlineKeyboard to cancel operation/state"""
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
    keyboard.add(button)
    return keyboard


def donate_keyboard():
    """Initialize InlineKeyboard for donate operation"""
    keyboard = InlineKeyboardMarkup()
    donate_1 = InlineKeyboardButton(text='1 EPIC', callback_data='donate_1')
    donate_5 = InlineKeyboardButton(text='5 EPIC', callback_data='donate_5')
    donate_x = InlineKeyboardButton(text='10 EPIC', callback_data='donate_10')
    button = InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
    keyboard.row(donate_1, donate_5, donate_x).add(button)
    return keyboard


def temp_storage():
    """Initialize temporary bot storage (pickle)"""
    pickle_storage = "tipbot_storage.pickle"

    try:
        storage = PickleStorage(pickle_storage)
    except EOFError:
        os.remove(pickle_storage)
        storage = PickleStorage(pickle_storage)

    return storage


COMMANDS = {'start': ['start', 'help', 'help@epic_vitex_bot', 'help@EpicTipBot', 'Start', 'Help', ],
            'create': ['create', 'register', 'Create', ],
            'balance': ['balance', 'bal', 'Balance', ],
            'address': ['address', 'deposit', 'Address', ],
            'history': ['history', 'transactions', ],
            'send': ['send', 'withdraw', ],
            'cancel': ['cancel'],
            'donation': ['donation', 'Donation', ],
            'tip': ['tip', 'Tip', 'TIP', ],
            'faq': ['faq', 'faq@EpicTipBot', 'Faq', ],
            # GUI / Keyboards / includes
            'wallet': ['wallet', 'wallet@EpicTipBot', 'Wallet', ]
            }