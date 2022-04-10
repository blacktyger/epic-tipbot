from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import MessageToDeleteNotFound
from aiogram.contrib.fsm_storage.files import PickleStorage
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram import types
from typing import Union

import decimal
import os

from logger_ import logger


ctx = decimal.Context()
ctx.prec = 20


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


def get_receiver(message: types.Message) -> Union[str, None]:
    """
    Parse receiver username from user's messages
    :param message: types.Message (AIOGRAM)
    :return: receiver string or None
    """
    for match in message.entities:
        if match['type'] == 'mention':
            start = match['offset']
            stop = start + match['length']
            return message.text[start:stop].replace('@', '')

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