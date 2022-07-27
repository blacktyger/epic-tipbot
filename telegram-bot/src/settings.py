from json import JSONDecodeError
from decimal import Decimal
from typing import Union
import platform
import random
import json

import requests


class MarketData:
    btc_feed_url = "https://blockchain.info"
    epic_feed_url = "https://api.coingecko.com/api/v3"

    @classmethod
    def price_epic_vs(cls, currency: str):
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f"{cls.epic_feed_url}/simple/price?ids=epic-cash&vs_currencies={symbol}"
                data = json.loads(requests.get(url).content)
                return Decimal(data['epic-cash'][symbol.lower()])
            except JSONDecodeError as er:
                print(er)
                return 0

    @classmethod
    def price_btc_vs(cls, currency: str):
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f"{cls.btc_feed_url}/ticker"
                data = json.loads(requests.get(url).content)
                return Decimal(data[symbol]['last'])
            except JSONDecodeError as er:
                print(er)
                return 0

    @classmethod
    def currency_to_btc(cls, value: Union[Decimal, float, int], currency: str):
        """Find bitcoin price in given currency"""
        symbol = currency.upper()
        if len(symbol) == 3:
            try:
                url = f'{cls.btc_feed_url}/tobtc?currency={currency}&value={value}'
                data = json.loads(requests.get(url).content)
                return Decimal(data)
            except JSONDecodeError as er:
                print(er)
                return 0


class Network:
    class VITE:
        name = 'VITE'
        symbol = 'VITE'
        is_token = True
        is_native = False
        fee = 0

    class EPIC:
        name = 'EPIC-CASH'
        symbol = 'EPIC'
        is_token = False
        is_native = True
        fee = 0.007


class Tests:
    language = ['pl', 'en', 'es']
    username = [None, 'Mad Max', 'Dearey', 'Pecan', 'Maestro', 'Halfmast', None, 'Peep', 'Boomer',
                'Coach', None, 'Dirty', 'Harry', 'Peppermint', None, 'Cookie', 'Piglet']
    first_name = ['Amelia', 'Tomas', 'Homero', 'Celina', 'Macario', 'Cipriano',
                  'Fidel', 'Borja', 'Otilia', 'Esteban', 'Laura', 'Rodrigo']
    last_name = ['Ferguson', None, 'Burch', 'Levine', 'Porter', None,
                 'Sawyer', 'Cooley', 'Brennan', None, 'Burnett', 'Chang']

    def random_user(self):
        random_id = ''.join([str(random.randint(0, 9)) for x in range(10)])
        return dict(id=random_id, is_bot=True,
                    username=random.choice(self.username),
                    last_name=random.choice(self.last_name),
                    first_name=random.choice(self.first_name),
                    language_code=random.choice(self.language)
                    )


class Tipbot:
    MAINTENANCE = False
    MAX_RECEIVERS = 5
    TIME_LOCK = 2.2
    ADMIN_ID = '803516752'
    DONATION_ADDRESS = 'vite_0ab437d8a54d52abc802c0e75210885e761d328eaefed14204'
    HELP_STRING = \
        """
🤖 *Hey, I'm Epic-Cash Tip-Bot* 👋

To signup with new account:
👉 /create

▪️ You will receive one-time link with your wallet *seedphrase* and *Tip-Bot* account *password* - please save them somewhere safe! 

▪️ Now you can deposit Epic-Cash to your wallet from *Vite Mobile/Desktop or Web app*, more details at vite.org.

▪️ Anyone with Tip-Bot account can tip or be tipped by @username:

👉 tip @blacktyg3r 0.1

▪️ to manage your *Wallet*:
👉 /wallet

Need help? [@blacktyg3r](https://t.me/blacktyg3r)    
"""

    FAQ_STRING = \
        """
ℹ️ *Epic Tip-Bot FAQ*

👉 *What exactly is Tip-Bot Wallet?*
▪️ It is fully functional wallet on VITE blockchain connected to your account.

👉 *Do I need Vite app to use Tip Bot?*
▪️ You can start using Tip-Bot right away and receive tips, but to deposit or withdraw you will need [Vite wallet](https://app.vite.net/).

👉 *How much does it cost?*
▪️ Using Epic Tip-Bot is *free*, transactions are within a second and also *free* 🥳.

👉 *Is it safe?*
▪️ This is custodial solution, means software have access to your private keys. Although all security measures are in place, there is always risk of losing funds - *use only for low value operations and withdraw regularly!*

👉 *What should I do with it?*
▪️ Tip users you like, content creators, developers or just random people - it is entirely up to you!

👉 *Can I send EPIC to someone without Tip-Bot account?*
▪️ You can also send/withdraw from your wallet to any valid VITE address (starting with `vite_...`).

"""


if platform.system() == 'Windows':
    class Database:
        API_PORT = 8000
        TIPBOT_URL = f"http://127.0.0.1:{API_PORT}/tipbot"
        API_URL = f"http://127.0.0.1:{API_PORT}/api"
else:
    class Database:
        API_PORT = 3273
        TIPBOT_URL = f"http://127.0.0.1:{API_PORT}/tipbot"
        API_URL = f"http://127.0.0.1:{API_PORT}/api"
