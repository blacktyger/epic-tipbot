import asyncio
from typing import Callable
import aiohttp
import socket
import json

from .logger_ import logger


DATABASE_SESSION = None
_lock = asyncio.Lock()


async def get_client_session():
    global DATABASE_SESSION

    async with _lock:
        if not DATABASE_SESSION:
            DATABASE_SESSION = aiohttp.ClientSession()

    return DATABASE_SESSION


class DatabaseManager:
    logger = logger
    API_PORT = 3273
    URL = f"http://127.0.0.1:{API_PORT}/api"

    def __init__(self):
        self.ports = self.Ports(call=self._call)
        self.wallets = self.Wallets(call=self._call)
        self.transactions = self.Transactions(call=self._call)

        if not self._ping_server():
            self.logger.error(f"Django database connection error: localhost:{self.API_PORT}")
            raise SystemExit(f"Database Connection Error") from None

    def _ping_server(self, timeout=1):
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('localhost', self.API_PORT))
        except OSError:
            return False
        else:
            s.close()
            return True

    async def _call(self, endpoint: str, params: dict, method: str) -> dict:
        """ Handle API calls to Django back-end database"""
        # Prepare database query
        full_url = f'{self.URL}/{endpoint}/'
        method = method.upper()

        if method == 'POST':
            kwargs = {'data': json.dumps(params)}
        else:
            for k, v in params.items():
                if isinstance(v, bool):
                    params[k] = str(v).lower()
            kwargs = {'params': params}

        print(kwargs)

        try:
            session = await get_client_session()
            response_ = await session.request(method, full_url, **kwargs)
            if response_.status != 200:
                logger.error(f'{full_url} | {response_.status}')
                response = {'error': 1, 'msg': 'Can not connect to database', 'data': None}
            else:
                r_json = await response_.json()

                try:
                    # try standard response scheme
                    if not r_json['error']:
                        msg = r_json['msg'] if 'msg' in r_json.keys() else 'success'
                        response = {'error': 0, 'msg': msg, 'data': r_json['data']}
                        logger.debug(f"tools::api_call({endpoint}) -> {r_json['msg']}")
                    else:
                        logger.warning(f"tools::api_call({endpoint}) -> {r_json['msg']}")
                        response = r_json
                except:
                    logger.debug(f"tools::api_call({endpoint}) (?)-> status {response_.status}")
                    response = {'error': 0, 'msg': 'success', 'data': r_json}

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Can not connect to {full_url} URL: {str(e)}")
            response = {'error': 1, 'msg': f"Database ReadTimeout / ConnectionError", 'data': None}

        return response

    class Transactions:
        def __init__(self, call: Callable):
            self._call = call

        async def get(self, params: dict):
            return await self._call(endpoint='transactions', method='get', params=params)

        async def post(self, params: dict):
            return await self._call(endpoint='save_transaction', method='post', params=params)

        async def update(self, params: dict):
            return await self._call(endpoint='update_transaction', method='post', params=params)

    class Wallets:
        def __init__(self, call: Callable):
            self._call = call

        async def get(self, params: dict):
            return await self._call(endpoint='wallets', method='get', params=params)

        async def post(self, params: dict):
            return await self._call(endpoint='save_wallet', method='post', params=params)

    class Ports:
        def __init__(self, call: Callable):
            self._call = call

        async def get(self, params: dict):
            return await self._call(endpoint='ports', method='get', params=params)

        async def post(self, params: dict):
            return await self._call(endpoint='ports', method='post', params=params)
