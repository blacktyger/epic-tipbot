import typing
import random

from aiogram.types import User

from . import tools, logger, DJANGO_API_URL
from .wallets import ViteWallet, EpicWallet
from .settings import Tests
from .ui import Interface


class TipBotUser(User):
    """
    Extend AIOGRAM User class with extra features
    """
    API_URL = DJANGO_API_URL

    def __init__(self, is_registered: bool = False, **kwargs: typing.Any):
        super().__init__(**kwargs)
        self.is_registered = is_registered
        self.vite_wallet = ViteWallet(owner=self)
        self.ui = Interface(self)

        # temp_user is used to access some instance methods,
        # in this case do not try to connect with database
        if 'temp_user' not in kwargs.keys():
            self.update_from_db()
            self.epic_wallet = EpicWallet(owner=self)

    @property
    def name(self):
        if self.username:
            return self.username
        else:
            return self.full_name

    @staticmethod
    def from_obj(user: User):
        """Create new object based on AIOGRAM User obj"""
        return TipBotUser(**user.__dict__['_values'])

    @staticmethod
    def from_dict(data: dict):
        """Create new object based on user dictionary"""
        print(data)
        return TipBotUser(**data)

    def _api_call(self, query: str, params: dict, method='get') -> dict:
        return tools.api_call(query, self.API_URL, params, method)

    def params(self):
        """Return user obj dictionary"""
        return self.__dict__['_values']

    def _update_to_db(self):
        """Update database with values from user obj, ID required"""
        if self.id:
            logger.info(f"@{self.name} TipBotUser::_update_to_db(users/create)")
            return self._api_call('users/create', self.params(), method='post')

    def _get_vite_wallet_from_db(self, address: str) -> None:
        self.vite_wallet.address = address
        logger.info(f"@{self.name} TipBotUser::_get_wallet_from_db() -> {self.vite_wallet}")

    def update_from_db(self):
        """
        Get TipBotUser data from Django Database, if exists save/update the data
        This method is used everytime when instance is created or registered to db.
        """
        need_update = False

        # Handle when ID, first_name and username is not present
        if not self.id and not self.first_name and not self.username:
            logger.error(f'No first_name, username and id')
            raise Exception(f'No first_name, username and id')

        # Send requests with params to database
        response = self._api_call('users', self.params())
        logger.info(f'{self.mention} TipBotUser::_update_from_db(users) -> {response["msg"]}')

        # Handle api_call error:
        if response['error']:
            logger.error(f'{self.mention} {response["msg"]}')
            return response

        # Handle no user/account case
        if not response['data']:
            self.is_registered = False
            logger.info(f'@{self.mention} Database query: {self.log_repr()}')

        # Handle multiple users matching to query
        elif len(response['data']) > 1:
            self.is_registered = False
            logger.warning(f'@{self.mention} Returned multiple users ({len(response["data"])}):'
                           f'\n{[(user["id"], user["first_name"]) for user in response["data"]]}')

        # Handle fetched user account
        else:
            self.is_registered = True

        if self.is_registered:
            # Save/Update params from database to object
            for key, value in response["data"][0].items():

                # Handle Wallet object creation
                if key == 'wallet':
                    try:
                        self._get_vite_wallet_from_db(address=value[0])
                    except Exception:
                        pass

                else:
                    # Handle data differences between database and user payload
                    # If user payload have different value database will be overwritten
                    value_from_user = str(getattr(self, key)) if getattr(self, key) else None
                    value_from_db = str(value)

                    if value_from_user and value_from_user != value_from_db:
                        need_update = True
                        logger.warning(f"@{self.mention} TipBotUser::_update_from_db({key}) NEED UPDATE: {getattr(self, key)} | (db): {value}")

                    # Handle saving values from database to instance
                    else:
                        setattr(self, key, value)

            # If any value in database was outdated update it
            if need_update:
                self._update_to_db()

    def register(self):
        """
        Handle Database API calls to create or update TipBot User
        """

        if 'id' not in self.params().keys():
            response = {'error': 1, 'msg': f'No user_id', 'data': None}

        elif 'first_name' not in self.params().keys():
            response = {'error': 1, 'msg': f'No first_name', 'data': None}

        else:
            response = self._update_to_db()

        if not response['error']:
            self.is_registered = True
            self.update_from_db()
            logger.info(f"@{self.mention} User::register() -> {response['msg']}")
        else:
            logger.warning(f"@{self.mention} User::register() -> {response['msg']}")

        return response

    def get_mention(self, name=None, as_html=None) -> str:
        if self.username:
            return f"@{self.username}"
        else:
            return f"[{self.name}]({self.url})"

    def get_url(self):
        """Prepare name and link to profile shown in messages"""
        return self.get_mention().replace('_', '\_')

    @classmethod
    def get_user(cls, key_word):
        """Get user from database without ID"""
        # Create temp user to access class method (cls)
        temp_user = cls(id=545454, temp_user=True)

        # List of possible params to query with key_word
        possible_params = ['username', 'first_name', 'part_username']

        for param in possible_params:
            params = {param: key_word}
            response = temp_user._api_call(query='users', params=params)
            print(param, response)

    def query_users(self, num: int, match: str):
        params = {'part_username': match}
        response = self._api_call(query='users', params=params)

        # Handle api_call error:
        if response['error']:
            logger.error(f'@{self.name} {response["msg"]}')
            return

        return response['data'][:num]

    def get_users(self, num: int, random_: bool = False):
        response = self._api_call(query='users', params={})

        # Handle api_call error:
        if response['error']:
            logger.error(f'@{self.name} {response["msg"]}')
            return

        if random_:
            random.shuffle(response['data'][0])

        return response['data'][:num]

    def log_repr(self) -> str:
        """Prepared string to log user details"""
        return f"User({self.id} | {self.name} | registered: {self.is_registered})"

    @classmethod
    def create_test_user(cls):
        """Create test user from random data and return self instance"""
        return cls(**Tests().random_user())

    def __str__(self):
        return self.log_repr()

    def __repr__(self):
        return self.log_repr()
