from json import JSONDecodeError
from dill import Pickler, Unpickler
import asyncio
import decimal
import random
import shelve
import socket
import json
import os

from aiogram.contrib.fsm_storage.files import PickleStorage
import requests
import aiohttp

from .database import DatabaseManager
from .settings import Database, EPIC
from .logger_ import logger


ctx = decimal.Context()
ctx.prec = 20
API_PORT = Database.API_PORT
DJANGO_API_URL = Database.API_URL
TIPBOT_API_URL = Database.TIPBOT_URL
owner_ports_file = os.path.join(EPIC.wallets_dir, '.owner_ports')
shelve.Pickler = Pickler
shelve.Unpickler = Unpickler

class SimpleDatabase:
    def __init__(self):
        self.db_file = 'simple.db'

    def update(self, key, value):
        with shelve.open(self.db_file) as db:
            db[key] = value

    def get(self, key):
        with shelve.open(self.db_file) as db:
            return db.get(key)


storage = SimpleDatabase()


class PortManager:
    db = DatabaseManager()
    api_url = f"{TIPBOT_API_URL}/ports/"
    ports_range = (5000, 60000)

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def _get_random_port(self):
        port_ = random.randint(self.ports_range[0], self.ports_range[1])

        while self._is_port_in_use(port_):
            port_ = random.randint(self.ports_range[0], self.ports_range[1])

        return port_

    def set_port(self):
        port = self._get_random_port()
        response = self.db.ports.post({'port': port})

        while response['error']:
            logger.warning(response)
            response = self.db.ports.post({'port': port})

        return response['data']


def delete_lock_files(directory: str = None, filename: str = None):
    if directory is None:
        directory = './wallets'

    if filename is None:
        filename = '.lock'

    for root, dirs, files in os.walk(directory):
        if filename in files:
            file_path = os.path.join(root, filename)
            os.remove(file_path)
            print(f"Deleted file: {file_path}")


def temp_storage():
    """Initialize temporary bot storage (pickle)"""
    pickle_storage = "tipbot_storage.pickle"

    try:
        storage_ = PickleStorage(pickle_storage)
    except EOFError:
        os.remove(pickle_storage)
        storage_ = PickleStorage(pickle_storage)

    return storage_


class MarketData:
    btc_feed_url = "https://blockchain.info"
    epic_feed_url = "https://api.coingecko.com/api/v3"

    @classmethod
    async def price_epic_vs(cls, currency: str):
        symbol = currency.upper()
        interval = 60

        if len(symbol) == 3:
            url = f"{cls.epic_feed_url}/simple/price?ids=epic-cash&vs_currencies={symbol}"

            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        async with await session.request('GET', url) as response:
                            json_response = await response.json(content_type=None)
                            price = decimal.Decimal(json_response['epic-cash'][symbol.lower()])
                            storage.update(key='epic_vs_usd', value=price)
                    except (KeyError, JSONDecodeError) as er:
                        logger.error(f"price_epic_vs: {er}")

                    await asyncio.sleep(interval)

    @classmethod
    def price_btc_vs(cls, currency: str):
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f"{cls.btc_feed_url}/ticker"
                data = json.loads(requests.get(url).content)
                return decimal.Decimal(data[symbol]['last'])
            except JSONDecodeError as er:
                print(er)
                return 0

    @classmethod
    def currency_to_btc(cls, value: decimal.Decimal | float | int, currency: str):
        """Find bitcoin price in given currency"""
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f'{cls.btc_feed_url}/tobtc?currency={currency}&value={value}'
                data = json.loads(requests.get(url).content)
                return decimal.Decimal(data)
            except JSONDecodeError as er:
                print(er)
                return 0


async def fee_wallet_update(mnemonics: str, address_id: str | int):
    url = f"{TIPBOT_API_URL}/update/"
    params = {'external_wallet': True, 'mnemonics': mnemonics, 'address_id': address_id}

    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, data=json.dumps(params), timeout=60 * 5) as resp:
                response = await resp.json()
                if response['data']:
                    if 'unreceived' in response['data']:
                        logger.info(f"FEE WALLET: {response['data']['unreceived']} new transactions")

        await asyncio.sleep(60)


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
        try:
            log_id = params['sender']['id']
        except:
            pass

    if not ping_server():
        response = {'error': 1, 'msg': f"Database Connection Error", 'data': None}
        return response

    try:
        if 'get' in method:
            response = requests.get(url=full_url, params=params, timeout=60 * 5)
        else:  # 'post' in method
            response = requests.post(url=full_url, data=json.dumps(params), timeout=60 * 5)

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
                    logger.debug(f"@{log_id} tools::api_call({query}) -> {r_json['msg']}")
                else:
                    logger.warning(f"@{log_id} tools::api_call({query}) -> {r_json['msg']}")
                    response = r_json
            except:
                logger.debug(f"@{log_id} tools::api_call({query}) (?)-> status 200")
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
