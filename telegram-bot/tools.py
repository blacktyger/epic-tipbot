from aiogram import types
from typing import Union
import decimal


def kill_markdown(string):
    return string.replace('*', '')


ctx = decimal.Context()
ctx.prec = 20

def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')

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


def parse_tip_command(message: types.Message, amount: Union[float, decimal.Decimal, int]) -> dict:
    """Return data for quick transaction"""

    # Check if command have enough params
    if len(message.entities) < 2:
        response = {'error': 1, 'msg': 'Receiver not recognized', 'data': None}

    elif len(message.entities) == 2:
        sender, _ = parse_user_and_message(message)
        receiver = {'username': message.parse_entities().replace('@', '').split(' ')[-1]}

        data = {
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'address': None
            }
        response = {'error': 0, 'msg': 'Success', 'data': data}

    else:
        response = {'error': 1, 'msg': 'Wrong command syntax', 'data': None}

    return response


def parse_send_command(message: types.Message) -> dict:
    """Return dict with data for transaction, pre-validation"""
    receiver = None
    address = None

    # Check if command have enough params
    if 3 <= len(message.text.split(' ')) < 5:

        # Validate amount
        amount = get_cmd_value(message, index=1)
        try:
            amount = float(amount)
            if amount <= 0:
                return {'error': 1, 'msg': 'Wrong amount value', 'data': None}
        except Exception as e:
            print(e)
            return {'error': 1, 'msg': 'Wrong amount value', 'data': None}

        # Get sender
        sender, _ = parse_user_and_message(message)

        # Check if receiver is TelegramUser
        if len(message.entities) == 2:
            receiver = message.entities[-1].user

            if receiver:
                if receiver.username:
                    username = receiver.username
                    mention = receiver.mention
                else:
                    username = receiver.first_name
                    mention = receiver.get_mention(username)
            else:
                username = message.parse_entities().split('@')[-1]
                mention = f"@{username}"

            receiver = {'username': username, 'mention': mention}

        # Check if receiver is vite address
        else:
            # Validate address
            address = get_cmd_value(message, index=2)
            if not is_valid_address(address):
                return {'error': 1, 'msg': 'Invalid receiver address', 'data': None}

        data = {
            'sender': sender,
            'receiver': receiver,
            'address': address,
            'amount': amount
            }

        return {'error': 0, 'msg': 'Success', 'data': data}
    else:
        return {'error': 1, 'msg': 'Wrong command syntax', 'data': None}


def is_valid_address(address: str) -> bool:
    return len(address) == 55 and address.startswith('vite_')


def is_valid_cmd(message: types.Message) -> bool:
    msg_parts = message.text.split(' ')
    return len(msg_parts) > 1


def vitescan_tx_url(tx_hash):
    return f"https://vitescan.io/tx/{tx_hash}"


def get_cmd_value(message: types.Message, index: Union[str, int] = 'last') -> Union[str, list]:
    msg_parts = message.text.split(' ')
    if index == 'last':
        return msg_parts[-1].strip()
    elif index == 'first':
        return msg_parts[1].strip()
    elif isinstance(index, int):
        return msg_parts[index].strip()
    else:
        return [msg.strip() for msg in msg_parts[1:]]
