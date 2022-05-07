from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, User
from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageCantBeDeleted
from aiogram.contrib.fsm_storage.files import PickleStorage
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram import types
import requests

import decimal
import random
import typing
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


def get_amount(message: types.Message) -> typing.Union[float, None]:
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
        self.cached_balance = dict
        self._update_from_db()

    def _update_from_db(self):
        if not self.address:
            logger.error(f'No address provided.')
            pass
        else:
            # Prepare database query
            query = 'wallets'
            params = {'address': self.address}
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
        request_data = {'address': self.address, 'id': None}

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

        if isinstance(response['data'], dict):
            if response['data'] and 'EPIC' in response['data'].keys():
                epic_balance = float_to_str(response['data']['EPIC'])
            else:
                epic_balance = 0.0

            # Get Epic-Cash price in USD from Coingecko API
            epic_vs_usd = PRICE.price_epic_vs('USD')
            balance_in_usd = f"{round(decimal.Decimal(epic_balance) * epic_vs_usd, 2)} USD" if epic_vs_usd else ''

            response['data']['string'] = epic_balance, balance_in_usd

            self.cached_balance = response
            return response

        else:
            return {'error': 0, 'msg': response['msg'], 'data': None}

    def __repr__(self):
        return f"TipBotWallet({self.address})"


class TipBotUser(User):
    """
    Extend AIOGRAM User class with extra features
    """
    def __init__(self, is_registered: bool = False, **kwargs: typing.Any):
        super().__init__(**kwargs)
        self.wallet = TipBotWallet()
        self.is_registered = is_registered
        self._update_from_db()

    @staticmethod
    def from_obj(user: User):
        # Create new objects based on AIOGRAM User class
        return TipBotUser(**user.__dict__['_values'])

    @staticmethod
    def from_dict(data: dict):
        # Create new objects based on user dictionary
        return TipBotUser(**data)

    @staticmethod
    def _api_call(query: str, url: str, params: dict, method='get') -> dict:
        # Prepare database query
        full_url = f'{url}/{query}/'

        if 'get' in method:
            response = requests.get(url=full_url, params=params)
        else:
            response = requests.post(url=full_url, data=json.dumps(params))

        if response.status_code != 200:
            return {'error': 1, 'msg': f'Database connection error {response.status_code}', 'data': None}

        return response.json()

    def register(self) -> dict:
        """
        Handle Database API calls to create new TipBot User
        """
        params = self.__dict__['_values']
        response = self._api_call(query='users/create', url=DJANGO_API_URL,
                                  params=params, method='post')

        if not response['error']:
            self.is_registered = True
            self._update_from_db()

        return response

    def _update_from_db(self) -> None:
        """
        Fetch TipBotUser data from Django Database based on TelegramUser ID
        If exists save/update the data
        """

        # Handle when both ID and username is not present
        if not self.id and self.username:
            logger.error(f'No username and id')
            raise Exception(f'No username and id')

        # Prepare params and send requests to database
        params = {'user_id': self.id, 'username': self.username}
        response = self._api_call('users', DJANGO_API_URL, params)

        # Handle no user/account case
        if not response:
            logger.warning(f'TelegramUser [{self.id}] {self.full_name} is not registered')
        else:
            self.is_registered = True

        if self.is_registered:
            # Save all params from database to object
            for key, value in response[0].items():
                if key == 'wallet':
                    print(key, value)
                    setattr(self, key, TipBotWallet(address=value[0]))
                else:
                    setattr(self, key, value)

    def get_url(self):
        # Prepare name and link to profile shown is messages
        # return f"[{self.name.capitalize()}](tg://user?id={self.id})"
        return self.get_mention()

    def query_users(self, num: int, match: str):
        params = {'part_username': match}
        response = self._api_call(query='users', url=DJANGO_API_URL, params=params)

        if 'error' not in response.keys():
            return response[:num]

    def get_users(self, num: int, random_: bool = False):
        response = self._api_call(query='users', url=DJANGO_API_URL, params={})

        if 'error' not in response.keys():
            if random_:
                random.shuffle(response[0])

            return response[:num]

    def __str__(self):
        return f"User[{self.full_name}, in_database: {self.is_registered}]"

    def __repr__(self):
        return self.__str__()

def get_receivers(message: types.Message) -> list:
    """
    Parse receiver username(s) from user's messages
    :param message: types.Message (AIOGRAM)
    :return: receivers list
    """

    receivers = []

    if len(message.entities) > 0:
        for match in message.entities:
            if 'mention' in match['type']:
                start = match['offset']
                stop = start + match['length']
                receivers.append(message.text[start:stop].replace('@', '').lower())
        return receivers
    else:
        try:
            receivers.append(message.parse_entities().split(' ')[1].lower())
        except Exception as e:
            logger.error(f'Error parsing receiver {e}')

    return receivers


def get_address(message: types.Message) -> typing.Union[str, None]:
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
    receiver = [{'username': user} for user in get_receivers(message)]
    amount = get_amount(message)

    if not receiver:
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
    receiver = {'username': get_receivers(message)[0]}
    sender, _ = parse_user_and_message(message)

    logger.info(f"{amount} {sender['username']} --> {receiver['username']} {address}")

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


class WalletGUI:
    """
    Manage different keyboards and GUI messages ('screens')
    """
    def __init__(self, user: TipBotUser, callback: CallbackData):
        self.user = user
        self.callback = callback

    def home_keyboard(self) -> InlineKeyboardMarkup:
        """
        Prepare Wallet GUI InlineKeyboard
        :return: InlineKeyboardMarkup instance (aiogram)
        """

        buttons = ['deposit', 'withdraw', 'send', 'donate', 'support']
        icons = ['↘ ', '↗️ ', '➡️ ', '❤️ ', '💬️ ']

        buttons = [InlineKeyboardButton(
            text=f"{icons[i]}{btn.capitalize()}",
            callback_data=self.callback.new(action=btn, user=self.user.id, username=self.user.username))
            for i, btn in enumerate(buttons)]

        keyboard_inline = InlineKeyboardMarkup() \
            .row(buttons[0], buttons[1]) \
            .row(buttons[2], buttons[3]) \
            .add(buttons[4])

        return keyboard_inline


async def delete_message(message: types.Message):
    """
    Wrapper function with try, except block
    around removing TelegramMessages
    """

    try:
        await message.delete()
    except (MessageToDeleteNotFound, MessageCantBeDeleted) as e:
        logger.error(f"{message.from_user.username}: {e}")
        pass


async def remove_state_messages(state: FSMContext):
    """Remove bot messages saved in temp storage"""
    state_ = await state.get_state()

    if state_:
        data = await state.get_data()

        # Remove messages
        if f'msg_{state_.split(":")[-1]}' in data.keys():
            msg = data[f'msg_{state_.split(":")[-1]}']
            try:
                logger.info(f"DELETE MSG: {msg['id']}")
            except Exception:
                pass

            await delete_message(msg)


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
    donate_10 = InlineKeyboardButton(text='10 EPIC', callback_data='donate_10')
    button = InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
    keyboard.row(donate_1, donate_5, donate_10).add(button)
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