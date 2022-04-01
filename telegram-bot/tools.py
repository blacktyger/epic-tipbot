from aiogram import types
from typing import Union
import decimal

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
    user = message.from_user.__dict__['_values']
    if 'username' not in user.keys():
        user['username'] = user['first_name']

    msg = {
        'id': message.message_id,
        'date': message.date.timestamp(),
        'text': message.text,
        'chat': message.chat.__dict__['_values'],
        'entities': message.entities[0].__dict__['_values'],
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

    print(amount, sender['username'], '-->', receiver['username'], address)

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
    return len(address) == 55 and address.startswith('vite_')


def vitescan_tx_url(tx_hash):
    return f"https://vitescan.io/tx/{tx_hash}"

