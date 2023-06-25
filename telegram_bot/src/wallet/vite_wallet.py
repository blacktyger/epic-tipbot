from decimal import Decimal
import threading
import asyncio

from aiogram.types import ParseMode
from aiogram import types

from .. import tools, logger, Tipbot, bot, settings, fees
from .base_wallet import Wallet


MD = ParseMode.MARKDOWN


class ViteWallet(Wallet):
    """
    Wallet class to manage VITE blockchain operations.
    Epic asset: EPIC-002 TOKEN
    """
    LOW_BALANCE_MSG = f"🟡 Insufficient balance"
    Fee = fees.ViteFee

    def __init__(self, owner: object, address: str = None):
        super().__init__(owner=owner, network=settings.Network.VITE.name)
        self.is_updating = False
        self.last_balance = {}

        if self.is_valid_address(address):
            self._update_from_db()

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

    def _send_fee(self):
        tx = self._build_transaction(amount=self.Fee.WITHDRAW, address=self.Fee.ADDRESS, type_of='fee')
        response = self._api_call('send_transaction', tx, method='post', api_url=self.API_URL2)

        if response['error']:
            logger.error(f"ViteWallet::withdraw()::fee_tx - {self.owner.mention}: {response['msg']}")
        else:
            logger.info(f"Fee({self.Fee.WITHDRAW}) from {self.owner.mention} sent")

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
            logger.error(f'@{self.owner.name} ViteWallet::update_balance() -> {response["msg"]}')
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
        self._send_fee()

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
            params = {
                'sender': self.owner.params(),
                'receiver': receiver.params(),
                'amount': data['amount'],
                'type_of': 'send',
                'network': settings.Network.VITE.symbol
                }

            response = self._api_call('send_transaction', params, method='post', api_url=self.API_URL2)

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
            if i+1 == len(data['recipients']):
                await state.finish()
                await query.answer()

            logger.critical(f"{self.owner.mention}: sent {amount} to {receiver.mention}")

            # Run threading process to update receiver balance (receiveTransactions call)
            logger.critical(f"{receiver.mention} ViteWallet::gui::send_tip() - start balance update")
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
                await message.edit_text(text=f"{message.text} ({i+1}/{len(payload['receivers'])})")
                await asyncio.sleep(settings.Tipbot.TIME_LOCK)

            # Build and send tip transaction
            params = {
                'sender': payload['sender'].params(),
                'amount': payload['amount'],
                'network': settings.Network.VITE.symbol,
                'type_of': 'tip',
                'receiver': receiver.params()
                }

            logger.critical(f"@{payload['sender'].name} ViteWallet::send_tip ({payload['amount']} -> {receiver.mention})")
            response = self._api_call('send_transaction', params, method='post', api_url=self.API_URL2)

            # Handle error from VITE network
            if response['error']:
                if 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"Your wallet is empty 🕸"
                else:
                    msg = f"{response['msg']}"
                finished_transactions.append({'error': 1, 'msg': msg, 'data': None})
            else:
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
        return f"Wallet({self.network} | {self.short_address})"


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

