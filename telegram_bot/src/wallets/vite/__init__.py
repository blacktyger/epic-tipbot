from decimal import Decimal
from typing import Any
import threading
import asyncio
import time

from aiogram.types import ParseMode
from aiogram import types

from ... import tools, logger, Tipbot, bot, settings, fees, DJANGO_API_URL, TIPBOT_API_URL


MD = ParseMode.MARKDOWN
storage = tools.storage


class ViteWallet:
    """
    Wallet class to manage VITE blockchain operations.
    Epic asset: EPIC-002 TOKEN
    """
    LOW_BALANCE_MSG = f"🟡 Insufficient balance"
    API_URL1 = DJANGO_API_URL
    API_URL2 = TIPBOT_API_URL
    NETWORK = settings.VITE.name
    Fee = fees.ViteFee

    def __init__(self, owner: Any, address: str = None):
        self.owner = owner
        self.storage = storage
        self._address = address
        self.is_updating = False
        self.last_balance = {}

        if self.is_valid_address(address):
            self._update_from_db()

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = value
        self._update_from_db()

    def _build_transaction(self, **kwargs):
        """
        Helper method to build a transaction payload
        """
        return {
            # 'sender': kwargs['sender'].params() if 'sender' in kwargs else self.owner.params(),
            'sender': self.owner.params(),
            'amount': str(kwargs['amount']),
            'address': kwargs['address'] if 'address' in kwargs else None,
            'receiver': kwargs['receiver'].params() if 'receiver' in kwargs else None,
            'type_of': kwargs['type_of'],
            'network': self.NETWORK
            }

    def _api_call(self, query: str, params: dict, method='get', api_url=None) -> dict:
        if not api_url:
            api_url = self.API_URL1

        return tools.api_call(query, api_url, params, method)

    async def _get_fees(self, amount: str | int | Decimal | float, query, state):
        balance = self.epic_balance()

        if balance['error']:
            logger.error(f"ViteWallet::_get_fees()::epic_balance() - {self.owner.mention}: {balance['msg']}")
            await self.owner.ui.send_message(text=balance['msg'], chat_id=self.owner.id)
            await self.owner.ui.remove_state_messages(state)
            await query.answer()
            return

        # Update wallet balance if there are pending transactions
        if balance['data']['pending']:
            self.update_balance()
            balance = self.epic_balance()

        epic_balance = Decimal(balance['data']['string'][0])
        total_amount = Decimal(amount) + self.Fee.WITHDRAW

        if epic_balance < total_amount:
            logger.warning(f"ViteWallet::_get_fees() - {self.owner.mention}: {self.LOW_BALANCE_MSG}")
            text = f"{self.LOW_BALANCE_MSG}, {str(total_amount)} EPIC required."
            await self.owner.ui.send_message(text=text, chat_id=self.owner.id)
            await self.owner.ui.remove_state_messages(state)
            await query.answer()
            return

        return True

    def _send_fee(self, type_of: str, amount: float | int | str | Decimal = None) -> None:
        if type_of in ['withdraw']:
            value = self.Fee.WITHDRAW
        elif type_of in ['tip', 'send']:
            if not amount:
                logger.error(f"Invalid tip transaction amount: {amount}")
                return

            value = self.Fee.get_tip_fee(amount)
        else:
            logger.error(f"Invalid transaction type: {type_of}")
            return

        tx = self._build_transaction(amount=value, address=self.Fee.ADDRESS, type_of='fee')
        time.sleep(0.5)
        response = self._api_call('send_transaction', tx, method='post', api_url=self.API_URL2)

        if response['error']:
            # Sometimes failed if tx is sent too fast
            if 'calc PoW twice' in response['msg'] or 'verify prevBlock failed' in response['msg']:
                time.sleep(1)
                response = self._api_call('send_transaction', tx, method='post', api_url=self.API_URL2)

                if response['error']:
                    logger.error(f"ViteWallet()::_send_fee - {self.owner.mention}: {response['msg']}")
                else:
                    logger.info(f"Fee({value}) from {self.owner.mention} sent")

            else:
                logger.error(f"ViteWallet()::_send_fee - {self.owner.mention}: {response['msg']}")

        else:
            logger.info(f"Fee({value}) from {self.owner.mention} sent")

    def _update_from_db(self):
        if not self.address:
            logger.error(f'No address provided.')
            return

        # database query
        params = {'address': self.address, 'id': self.owner.id, 'first_name': self.owner.first_name, 'username': self.owner.username}
        response = self._api_call(query='wallets', params=params)

        if response['error']:
            logger.error(f'@{self.owner.name} ViteWallet::_update_from_db() -> {response["msg"]}')
            return

        for key, value in response.items():
            setattr(self, key, value)

    def get_mnemonics(self):
        """Get the wallet mnemonic seed phrase via OneTimeSecret link"""
        # Send POST request to get wallet mnemonic seed phrase
        response = self._api_call('get_mnemonics', params=self.owner.params(), method='post', api_url=self.API_URL2)

        if response['error']:
            logger.error(f'@{self.owner.mention} ViteWallet::get_mnemonics() -> {response["msg"]}')

        return response

    def epic_balance(self) -> dict:
        self.is_updating = True

        # Send POST request to get wallet balance from network
        params = {'address': self.address, 'id': self.owner.id, 'first_name': self.owner.first_name, 'username': self.owner.username}
        balance = self._api_call('balance', params, method='post', api_url=self.API_URL2)

        if balance['error']:
            self.is_updating = False
            self.last_balance = balance
        else:
            balances, pending = self.parse_vite_balance(balance['data'])

            if isinstance(balances, dict) and 'EPIC' in balances.keys():
                epic_balance = tools.float_to_str(balances['EPIC'])
            else:
                epic_balance = 0.0

            # Get Epic-Cash price in USD from Coingecko API
            epic_vs_usd = self.storage.get(key='epic_vs_usd')
            balance_in_usd = f"{round(Decimal(epic_balance) * epic_vs_usd, 2)} USD" if epic_vs_usd else ''

            self.last_balance = {'error': 0, 'msg': 'success', 'data': {
                'string': (epic_balance, balance_in_usd),
                'pending': pending}}
            self.is_updating = False

        return self.last_balance

    def update_balance(self):
        if self.is_updating:
            logger.warning('updating thread already running for this wallet instance')
            return True

        # Send POST request to update wallet balance (receiveTransactions call)
        self.is_updating = True
        params = {'address': self.address, 'id': self.owner.id, 'first_name': self.owner.first_name, 'username': self.owner.username}
        response = self._api_call('update', params, method='post', api_url=self.API_URL2)

        if response['error']:
            logger.error(f'@{self.owner.mention} ViteWallet::update_balance() -> {response["msg"]}')
            self.is_updating = False
            return

        self.is_updating = False

        return True

    @staticmethod
    def parse_vite_balance(data: dict):
        return tools.parse_vite_balance(data)

    @staticmethod
    def is_valid_address(address: str):
        """Validate Vite address"""
        address = str(address)
        return len(address) == 55 and address.startswith('vite_')

    @staticmethod
    def get_explorer_tx_url(tx_hash: str):
        """Create VITE explorer transaction URL"""
        return f"https://vitescan.io/tx/{tx_hash}"

    async def withdraw(self, state, query):
        """Used to withdraw to VITE address"""
        # Remove keyboard and display processing msg
        data = await state.get_data()
        text = f"⏳ Processing the transaction.."
        await data['msg_confirmation'].edit_text(text=text, reply_markup=None, parse_mode=MD)

        # Check wallet balance against full amount (with fees)
        if not await self._get_fees(data['amount'], query, state):
            return

        # Send withdraw transaction
        transaction = self._build_transaction(amount=data['amount'], address=data['address'], type_of='withdraw')
        response = self._api_call('send_transaction', transaction, method='post', api_url=self.API_URL2)

        if response['error']:
            if 'sendBlock.Height must be larger than 1' in response['msg']:
                msg = self.LOW_BALANCE_MSG
            else:
                msg = f"🟡 {response['msg']}"

            logger.error(f"ViteWallet::withdraw() - {self.owner.mention}: {response['msg']}")
            await self.owner.ui.send_message(text=msg, chat_id=self.owner.id)
            await self.owner.ui.remove_state_messages(state)
            await query.answer()
            return

        # Send fee transaction
        self._send_fee(type_of='withdraw')

        # Show user notification/alert
        await query.answer(text='Transaction Confirmed!')
        await asyncio.sleep(1)

        # Remove messages from previous state
        await self.owner.ui.remove_state_messages(state)

        # Create Vitescan.io explorer link to transaction
        transaction_hash = response['data']['hash']
        explorer_url = self.get_explorer_tx_url(transaction_hash)

        # Prepare user confirmation message
        amount = tools.float_to_str(data['amount'])
        private_msg = f"✅ *Withdraw success*\n▪️[Transaction details (vitescan.io)]({explorer_url})"

        # Send tx confirmation to sender's private chat
        await self.owner.ui.send_message(text=private_msg, chat_id=self.owner.id)

        # Finish withdraw state
        await state.finish()
        await query.answer()

        logger.info(f"{self.owner.mention}: sent {amount} to {data['address']}")

    async def send_to_users(self, state, query):
        """ Used to send to user """
        data = await state.get_data()
        logger.info(f"ViteWallet::send_to_user() - receiver data: {data['recipients']}")

        # Remove keyboard and display processing msg
        conf_msg = f"⏳ Processing transaction.."
        await data['msg_confirmation'].edit_text(text=conf_msg, reply_markup=None, parse_mode=MD)

        for i, receiver in enumerate(data['recipients']):
            # Consider anti-spam transaction lock
            if i > 0:
                await asyncio.sleep(settings.Tipbot.TIME_LOCK)

            # Build and send transaction
            transaction = self._build_transaction(amount=data['amount'], receiver=receiver, type_of='send')
            response = self._api_call('send_transaction', transaction, method='post', api_url=self.API_URL2)

            # Handle error case
            if response['error']:
                if 'no account' in response['msg']:
                    msg = f"🟡 @{data['recipient']['username']} have no Tip-Bot account yet."
                elif 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"🟡 Insufficient balance."
                else:
                    msg = f"🟡 {response['msg']}"

                logger.error(f"ViteWallet::send() - {self.owner.mention}: {response['msg']}")
                await self.owner.ui.send_message(text=msg, chat_id=self.owner.id)
                await self.owner.ui.remove_state_messages(state)
                await query.answer()
                return

            # Send fee transaction
            self._send_fee(type_of='send', amount=data['amount'])

            # Remove messages from previous state only at first iteration
            if i == 0:
                # Show user notification/alert
                await self.owner.ui.remove_state_messages(state)
                await query.answer(text='Transaction Confirmed!')
                await asyncio.sleep(1)

            # Create Vitescan.io explorer link to transaction
            transaction_hash = response['data']['hash']
            explorer_url = self.get_explorer_tx_url(transaction_hash)

            # Prepare user confirmation message
            amount = tools.float_to_str(data['amount'])
            private_msg = f"✅ Transaction sent successfully\n️️ [Transaction details (vitescan.io)]({explorer_url})"
            receiver_msg = f"💸 `{amount} EPIC` from {self.owner.get_url()}"

            # Send tx confirmation to sender's private chat
            await self.owner.ui.send_message(text=private_msg, chat_id=self.owner.id)

            # Send notification to receiver's private chat
            if not receiver.is_bot:
                await self.owner.ui.send_message(text=receiver_msg, chat_id=receiver.id)

            # Finish send state when last element from list
            if i + 1 == len(data['recipients']):
                await state.finish()
                await query.answer()

            logger.critical(f"{self.owner.mention}: sent {amount} to {receiver.mention}")

            # Run threading process to update receiver balance (receiveTransactions call)
            logger.warning(f"{receiver.mention} ViteWallet::gui::send_to_users() - start balance update")
            threading.Thread(target=receiver.wallet.update_balance).run()

    async def send_tip(self, payload: dict, message):
        finished_transactions = []
        success_transactions = 0

        # Handle when no valid receiver
        if not payload['receivers']:
            msg = f"Invalid recipient username."
            return {'error': 1, 'msg': msg, 'data': None}

        # Handle too many receivers:
        if len(payload['receivers']) > settings.Tipbot.MAX_RECEIVERS:
            msg = f"Too many receivers: {len(payload['receivers'])}, max: {settings.Tipbot.MAX_RECEIVERS}"
            return {'error': 1, 'msg': msg, 'data': None}

        # Handle wrong amount
        if not payload['amount'] or Decimal(payload['amount']) <= 0:
            return {'error': 1, 'msg': f"Wrong amount value.", 'data': None}

        # Iterate through list of receivers and send transaction to each
        for i, receiver in enumerate(payload['receivers']):
            # Respect anti-flood locking system
            if i > 0:
                await message.edit_text(text=f"{message.text} ({i + 1}/{len(payload['receivers'])})")
                await asyncio.sleep(settings.Tipbot.TIME_LOCK)

            # Build and send tip transaction
            transaction = self._build_transaction(amount=payload['amount'], receiver=receiver, type_of='tip')
            logger.critical(f"{self.owner.mention} ViteWallet::send_tip() ({payload['amount']} -> {receiver.mention})")
            response = self._api_call('send_transaction', transaction, method='post', api_url=self.API_URL2)

            # Handle error from VITE network
            if response['error']:
                if 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"Your wallet is empty 🕸"
                else:
                    msg = f"{response['msg']}"
                finished_transactions.append({'error': 1, 'msg': msg, 'data': None})
            else:
                # Send fee transaction
                self._send_fee(type_of='send', amount=payload['amount'])

                # Handle success transaction
                finished_transactions.append(response)
                success_transactions += 1

        return {'msg': f'send_tip success: {success_transactions}/{len(payload["receivers"])}',
                'error': 0, 'data': finished_transactions}

    async def show_deposit(self, query=None):
        params = dict(id=self.owner.id, username=self.owner.username, first_name=self.owner.first_name)
        response = self._api_call('address', params, method='post', api_url=self.API_URL2)

        if not response['error']:
            msg = f"👤  *Your ID & Username:*\n" \
                  f"`{self.owner.id}`  &  `{self.owner.mention}`\n\n" \
                  f"🏷  *VITE Network Deposit Address:*\n" \
                  f"`{response['data']}`\n"

        else:
            msg = f"🟡 Wallet error (deposit address)"
            logger.error(f"Wallet::show_deposit() - {self.owner.mention}: {response['msg']}")

        await bot.send_message(text=msg, chat_id=self.owner.id, parse_mode=MD)

        # Handle proper Telegram Query closing
        if query:
            await query.answer()

    @property
    def short_address(self) -> str:
        if self.address:
            return f"{self.address[0:8]}...{self.address[-4:]}"
        else:
            return f"No address"

    def __repr__(self):
        return f"Wallet({self.NETWORK} | {self.short_address})"


class AliasWallet:
    """Helper class to represent AccountAlias objects as TipBotUser like object"""
    def __init__(self, title: str = None, address: str = None, **kwargs):
        self.owner: object = None
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

        print(response)
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


async def welcome_screen(user, message):
    active_chat = message.chat.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'), caption=Tipbot.HELP_STRING, parse_mode=MD)

    if Tipbot.ADMIN_ID in str(user.id):
        await bot.send_media_group(chat_id=active_chat, media=media)
    else:
        await bot.send_media_group(chat_id=user.id, media=media)


async def faq_screen(user, message):
    active_chat = message.chat.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'), caption=Tipbot.FAQ_STRING, parse_mode=MD)

    if Tipbot.ADMIN_ID in str(user.id):
        await bot.send_media_group(chat_id=active_chat, media=media)
    else:
        await bot.send_media_group(chat_id=user.id, media=media)
