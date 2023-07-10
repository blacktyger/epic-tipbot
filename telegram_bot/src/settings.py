import random
import os

import tomlkit


class Database:
    API_PORT = 3273
    TIPBOT_URL = f"http://127.0.0.1:{API_PORT}/tipbot"
    API_URL = f"http://127.0.0.1:{API_PORT}/api"


class VITE:
    name = 'VITE'
    symbol = 'VITE'
    is_token = True
    is_native = False

class EPIC:
    name = 'EPIC'
    symbol = 'EPIC'
    network = 'EPIC'
    is_token = False
    is_native = True
    password = "test_password"
    wallets_dir = os.path.join(os.getcwd(), 'wallets')
    binary_file_path = "/home/blacktyger/epic-wallet/target/release/epic-wallet"
    node_address = "https://epic-radar.com/node"
    withdraw_wallet_path = "/home/blacktyger/epic-tipbot/telegram_bot/wallets/wallet_WITHDRAW/config.toml"

    def withdraw_address(self) -> str | None:
        try:
            with open(self.withdraw_wallet_path, 'rt', encoding="utf-8") as file:
                settings_ = tomlkit.load(file)

            print(settings_['epicbox_address'])
            return settings_['epicbox_address']
        except Exception as e:
            print(str(e))
            return


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
