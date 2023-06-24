from aiogram.contrib.fsm_storage.files import PickleStorage
import requests
import socket

import decimal
import json
import os

from .logger_ import logger
from .settings import Database, MarketData


ctx = decimal.Context()
PRICE = MarketData()
ctx.prec = 20
API_PORT = Database.API_PORT
DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL


def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')


def is_float(value):
    try:
        return float(value)
    except:
        return None


def is_int(value):
    try:
        return int(value)
    except:
        return None


def api_call(query: str, url: str, params: dict, method='get') -> dict:
    """ Handle API calls to Django back-end database
    :param query: str,
    :param url: str,
    :param params: dict,
    :param method: str,
    :return: dict
    """
    # Prepare database query
    full_url = f'{url}/{query}/'

    log_ids = ['username', 'first_name', 'id', 'user']
    log_id = None

    for match in log_ids:
        if match in params:
            log_id = params[match]
            break

    if not log_id:
        try: log_id = params['sender']['id']
        except: pass

    if not ping_server():
        response = {'error': 1, 'msg': f"Database Connection Error", 'data': None}
        return response

    try:
        if 'get' in method:
            response = requests.get(url=full_url, params=params, timeout=60*5)
        else:  # 'post' in method
            response = requests.post(url=full_url, data=json.dumps(params), timeout=60*5)

        if response.status_code != 200:
            logger.error(f'@{log_id} {full_url} | {response.status_code}')
            response = {'error': 1, 'msg': 'Can not connect to database', 'data': None}
        else:
            r_json = response.json()

            try:
                # try standard response scheme
                if not r_json['error']:
                    msg = r_json['msg'] if 'msg' in r_json.keys() else 'success'
                    response = {'error': 0, 'msg': msg, 'data': r_json['data']}
                    logger.info(f"@{log_id} tools::api_call({query}) -> {r_json['msg']}")
                else:
                    logger.warning(f"@{log_id} tools::api_call({query}) -> {r_json['msg']}")
                    response = r_json
            except:
                logger.info(f"@{log_id} tools::api_call({query}) (?)-> status 200")
                response = {'error': 0, 'msg': 'success', 'data': r_json}

    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        logger.error(f"@{log_id} Can not connect to {full_url} URL")
        response = {'error': 1, 'msg': f"Database ReadTimeout / ConnectionError", 'data': None}

    return response


def parse_vite_balance(data):
    """Parse Vite wallet balances from network"""
    balances = {'EPIC': 0}
    if 'balanceInfoMap' in data['balance'].keys():
        for token_id, token_details in data['balance']['balanceInfoMap'].items():
            token = token_details['tokenInfo']
            balance = int(token_details['balance']) / 10 ** token['decimals']
            balances[token['tokenSymbol']] = balance

    pending = int(data['unreceived']['blockCount'])

    return balances, pending


def ping_server(timeout=1):
    """ping server"""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', API_PORT))
    except OSError as error:
        return False
    else:
        s.close()
        return True


def temp_storage():
    """Initialize temporary bot storage (pickle)"""
    pickle_storage = "tipbot_storage.pickle"

    try:
        storage = PickleStorage(pickle_storage)
    except EOFError:
        os.remove(pickle_storage)
        storage = PickleStorage(pickle_storage)

    return storage

class DatabaseError(Exception):
    pass