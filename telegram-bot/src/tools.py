from aiogram.contrib.fsm_storage.files import PickleStorage
import requests

import decimal
import json
import os

from .logger_ import logger
from .settings import Database, MarketData


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


def api_call(query: str, url: str, params: dict, method='get', timeout=20) -> dict:
    """ Handle API calls to Django back-end database
    :param timeout: int
    :param query: str
    :param url: str
    :param params: dict
    :param method: str
    :return: dict
    """
    # Prepare database query
    full_url = f'{url}/{query}/'
    try:
        if 'get' in method:
            response = requests.get(url=full_url, params=params, timeout=timeout)
        else:  # 'post' in method
            response = requests.post(url=full_url, data=json.dumps(params), timeout=timeout)

        if response.status_code != 200:
            logger.error(f'{full_url} | {response.status_code}')
            response = {'error': 1, 'msg': 'Can not connect to database', 'data': None}
        else:
            r_json = response.json()
            try:
                # try standard response scheme
                if not r_json['error']:
                    msg = r_json['msg'] if 'msg' in r_json.keys() else 'success'
                    response = {'error': 0, 'msg': msg, 'data': r_json['data']}
                    logger.info(f"tools::api_call({query}) - db response: {r_json}")
                else:
                    logger.warning(f"tools::api_call({query}) - db response: {r_json}")
                    response = r_json
            except:
                logger.info(f"tools::api_call({query}) - db response(?): {r_json}")
                response = {'error': 0, 'msg': 'success', 'data': r_json}

    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        logger.error(f"Can not connect to {full_url} URL")
        response = {'error': 1, 'msg': f"Database ReadTimeout / ConnectionError", 'data': None}

    return response


def temp_storage():
    """Initialize temporary bot storage (pickle)"""
    pickle_storage = "tipbot_storage.pickle"

    try:
        storage = PickleStorage(pickle_storage)
    except EOFError:
        os.remove(pickle_storage)
        storage = PickleStorage(pickle_storage)

    return storage

