from .. import tools, DJANGO_API_URL, logger, TIPBOT_API_URL

class Wallet:
    """
    Base Wallet class for blockchain operations and Telegram management.
    """
    API_URL1 = DJANGO_API_URL
    API_URL2 = TIPBOT_API_URL

    def __init__(self,
                 owner: object,
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

    async def show_deposit(self, query=None):
        params = dict(id=self.owner.id, username=self.owner.username)
        response = self._api_call('address', params, method='post', api_url=self.API_URL2)

        if not response['error']:
            msg = f"👤  *Your ID & Username:*\n" \
                  f"`{self.owner.id}`  &  `{self.owner.mention}`\n\n" \
                  f"🏷  *VITE Network Deposit Address:*\n" \
                  f"`{response['data']}`\n"

        else:
            msg = f"🟡 Wallet error (deposit address)"
            logger.error(f"Wallet::show_deposit() - {self.owner.mention}: {response['msg']}")

        await self.owner.ui.send_message(text=msg, chat_id=self.owner.id)

        # Handle proper Telegram Query closing
        if query:
            await query.answer()
