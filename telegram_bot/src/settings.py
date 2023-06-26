import random
from .fees import ViteFee

class Database:
    API_PORT = 3273
    TIPBOT_URL = f"http://127.0.0.1:{API_PORT}/tipbot"
    API_URL = f"http://127.0.0.1:{API_PORT}/api"


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

▪️ You will receive one-time link with your wallet *seed phrase* and *Tip-Bot* account *password* - please save them somewhere safe! 

▪️ Now you can deposit Epic-Cash to your wallet from *Vite Mobile/Desktop or Web app*, more details at vite.org.

▪️ Anyone with Tip-Bot account can tip or be tipped by @username:

👉 tip @blacktyg3r 0.1

▪️ to manage your *Wallet*:
👉 /wallet

Need help? [@blacktyg3r](https://t.me/blacktyg3r)    
"""

    FAQ_STRING = \
        f"""
ℹ️ *Epic Tip-Bot FAQ*

👉 *What exactly is Tip-Bot Wallet?*
▪️ It is fully functional wallet on the VITE blockchain connected to your Telegram account.

👉 *Do I need Vite app to use Tip Bot?*
▪️ You can start using Tip-Bot right away and receive tips, but to deposit or withdraw you will need [Vite wallet](https://app.vite.net/).

👉 *How much does it cost?*
▪️ Using Epic Tip-Bot is *free*, transactions have fees, withdraw to other Vite wallets: *{ViteFee().fee_values()['withdraw']} EPIC* and Tip/Send: *{ViteFee().fee_values()['tip']}%*.

👉 *Is it safe?*
▪️ This is custodial solution, means software have access to your private keys. Although all security measures are in place, there is always risk of losing funds - *use only for low value operations and withdraw regularly!*

👉 *Can I send EPIC to someone without Tip-Bot account?*
▪️ You can also send/withdraw from your wallet to any valid VITE address (starting with `vite_...`).
"""
