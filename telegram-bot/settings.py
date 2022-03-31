import platform
from json import JSONDecodeError
from decimal import Decimal
from typing import Union
import json

import requests


class MarketData:
    btc_feed_url = "https://blockchain.info"
    epic_feed_url = "https://api.coingecko.com/api/v3"

    def price_epic_vs(self, currency: str):
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f"{self.epic_feed_url}/simple/price?ids=epic-cash&vs_currencies={symbol}"
                data = json.loads(requests.get(url).content)
                return Decimal(data['epic-cash'][symbol.lower()])
            except JSONDecodeError as er:
                print(er)
                return 0

    def price_btc_vs(self, currency: str):
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f"{self.btc_feed_url}/ticker"
                data = json.loads(requests.get(url).content)
                return Decimal(data[symbol]['last'])
            except JSONDecodeError as er:
                print(er)
                return 0

    def currency_to_btc(self, value: Union[Decimal, float, int], currency: str):
        """Find bitcoin price in given currency"""
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f'{self.btc_feed_url}/tobtc?currency={currency}&value={value}'
                data = json.loads(requests.get(url).content)
                return Decimal(data)
            except JSONDecodeError as er:
                print(er)
                return 0


class Tipbot:
    DEFAULT_TIP = 0.01


if platform.system() == 'Windows':
    class Database:
        TIPBOT_URL = "http://127.0.0.1:8000/tipbot"
        API_URL = "http://127.0.0.1:8000/api"
        API_GET_BLOCKS = "block/"
else:
    class Database:
        TIPBOT_URL = "http://127.0.0.1:3273/tipbot"
        API_URL = "http://127.0.0.1:3273/api"
        API_GET_BLOCKS = "block/"



