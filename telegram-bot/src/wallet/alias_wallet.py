from .. import tools, DJANGO_API_URL, TIPBOT_API_URL, logger

class Wallet:
    """Helper class to represent AccountAlias objects as TipBotUser like object"""

    def __init__(self, title: str = None, address: str = None, **kwargs):
        self.owner = None
        self.title = title.replace('#', '')
        self.is_bot = True
        self.address = address

        for arg, val in kwargs.items():
            setattr(self, arg, val)

    def register(self):
        if self.address and self.title and self.owner.is_registered:
            return self._update_to_db()

    def get(self):
        """Get Alias info from database, return updated AliasWallet instance"""
        if self.title:
            response = tools.api_call('alias', DJANGO_API_URL, dict(title=self.title), 'get')
        elif self.address:
            response = tools.api_call('alias', DJANGO_API_URL, dict(address=self.address), 'get')
        else:
            raise Exception('#ALIAS or ADDRESS must be provided.')

        if response['data']:
            for arg, val in response['data'][0].items():
                setattr(self, arg, val)

            return self
        else:
            return None

    def balance(self):
        response = tools.api_call('balance', TIPBOT_API_URL, self.params(), 'post')
        if response['error']:
            return 0

        return response['data']

    def _update_to_db(self):
        """Send instance to the database and create/update entry."""
        params = self.params()
        if 'is_bot' in params: del params['is_bot']

        return tools.api_call('create_alias', TIPBOT_API_URL, self.params(), 'post')

    def params(self) -> dict:
        """Return user obj dictionary"""
        # Serialize owner object to 'id' int type
        params = self.__dict__

        if not isinstance(self.owner, int):
            try: params['owner'] = int(self.owner.id)
            except: params['owner'] = params['owner']

        return params

    def get_url(self) -> str:
        return f"#**{self.title}**"

    def short_address(self) -> str:
        if self.address:
            return f"{self.address[0:8]}...{self.address[-4:]}"
        else:
            return f"No address"

    def __str__(self):
        return f"AliasReceiver(#{self.title}, {self.short_address()})"

    def __repr__(self):
        return f"AliasReceiver(#{self.title}, {self.short_address()})"
