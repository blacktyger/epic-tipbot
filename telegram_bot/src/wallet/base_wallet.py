from .. import tools, DJANGO_API_URL, logger, TIPBOT_API_URL

class Wallet:
    """
    Base Wallet class for blockchain operations and Telegram management.
    """
    API_URL1 = DJANGO_API_URL
    API_URL2 = TIPBOT_API_URL

    def __init__(self,
                 owner,
                 network: str,
                 address: str = None,
                 ):
        self.owner = owner
        self.network = network
        self._address = address

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = value
        self._update_from_db()

    def _api_call(self, query: str, params: dict, method='get', api_url=None) -> dict:
        if not api_url:
            api_url = self.API_URL1

        return tools.api_call(query, api_url, params, method)

    def _update_from_db(self):
        pass

    def epic_balance(self) -> dict:
        pass

    def withdraw(self, state, query):
        pass

    def send_to_user(self, state, query):
        pass

    def tip_user(self):
        pass

