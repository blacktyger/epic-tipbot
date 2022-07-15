from aiogram.types import ParseMode
from aiogram import types
import requests

import threading
import decimal
import json
import time

from .base_wallet import Wallet
from .. import tools, logger, TIPBOT_API_URL, Tipbot, bot, settings, DJANGO_API_URL


class ViteWallet(Wallet):
    """
    Wallet class to manage VITE blockchain operations.
    Epic asset: EPIC-002 TOKEN
    """

    def __init__(self, owner: object, address: str):
        super().__init__(owner=owner, address=address, network=settings.Network.VITE.name)
        if not self.is_valid_address(address):
            raise Exception("Invalid VITE address")

        self.address = address
        self._update_from_db()

    def epic_balance(self) -> dict:
        # Send POST request to get wallet balance from network
        params = {'address': self.address, 'id': self.owner.id}
        balance = self._api_call('balance', params, method='post', api_url=self.API_URL2)
        # pprint(balance)

        if balance['error']: return balance

        wallet_balance = self.parse_vite_balance(balance['data'])

        if isinstance(wallet_balance, dict) and 'EPIC' in wallet_balance.keys():
            epic_balance = tools.float_to_str(wallet_balance['EPIC'])
        else:
            epic_balance = 0.0

        # Get Epic-Cash price in USD from Coingecko API
        epic_vs_usd = settings.MarketData().price_epic_vs('USD')
        balance_in_usd = f"{round(decimal.Decimal(epic_balance) * epic_vs_usd, 2)} USD" if epic_vs_usd else ''

        wallet_balance['string'] = epic_balance, balance_in_usd
        response = {'error': 0, 'msg': 'success', 'data': wallet_balance}

        if balance['data']['pending']:
            response['msg'] = 'pendingTransactions'
            response['data']['pending'] = balance['data']['pending']

        return response

    def update_balance(self, num: int = 1):
        # Send POST request to update wallet balance (receiveTransactions call)
        params = {'address': self.address, 'id': self.owner.id, 'num': num}
        response = self._api_call('update', params, method='post', api_url=self.API_URL2)

        if response['error']:
            logger.error(f'ViteWallet::update_balance() - {response["msg"]}')
            return

        return True

    @staticmethod
    def parse_vite_balance(data: dict):
        """Helper to parse Vite wallet balances from network"""
        balances = {}

        if 'balanceInfoMap' in data.keys():
            for token_id, token_details in data['balanceInfoMap'].items():
                token = token_details['tokenInfo']
                balance = int(token_details['balance']) / 10 ** token['decimals']
                balances[token['tokenSymbol']] = balance

        return balances

    def _update_from_db(self):
        if not self.address:
            logger.error(f'No address provided.')
            return

        # database query
        params = {'address': self.address, 'id': self.owner.id}
        response = self._api_call(query='wallets', params=params)

        if response['error']:
            logger.error(f'ViteWallet::_update_from_db() - {response["msg"]}')
            return

        for key, value in response.items():
            setattr(self, key, value)

    @staticmethod
    def is_valid_address(address: str):
        """Validate Vite address"""
        return len(address) == 55 and address.startswith('vite_')

    @staticmethod
    def get_explorer_tx_url(tx_hash: str):
        """Create VITE explorer transaction URL"""
        return f"https://vitescan.io/tx/{tx_hash}"

    def donate_dev(self):
        pass

    async def withdraw(self, state, query):
        """Used to withdraw to VITE address"""
        # Remove keyboard and display processing msg
        data = await state.get_data()
        conf_msg = f"⏳ Processing transaction.."
        await data['msg_confirmation'].edit_text(text=conf_msg, reply_markup=None,
                                                 parse_mode=ParseMode.MARKDOWN)
        # Build and send withdraw transaction
        params = {
            'sender': self.owner.params(),
            'amount': data['amount'],
            'address': data['address'],
            'type_of': 'withdraw',
            'network': settings.Network.VITE.symbol
            }

        response = self._api_call('send_transaction', params, method='post', api_url=self.API_URL2)

        if response['error']:
            if 'sendBlock.Height must be larger than 1' in response['msg']:
                msg = f"🟡 Insufficient balance."
            else:
                msg = f"🟡 {response['msg']}"

            logger.error(f"ViteWallet::withdraw() - {self.owner.mention}: {response['msg']}")
            await self.gui.send_message(text=msg, chat_id=self.owner.id)
            await self.gui.remove_state_messages(state)
            await query.answer()
            return

        # Show user notification/alert
        await query.answer(text='Transaction Confirmed!')
        time.sleep(1)

        # Remove messages from previous state
        await self.gui.remove_state_messages(state)

        # Create Vitescan.io explorer link to transaction
        transaction_hash = response['data']['hash']
        explorer_url = self.get_explorer_tx_url(transaction_hash)

        # Prepare user confirmation message
        amount = tools.float_to_str(data['amount'])
        private_msg = f"✅ *Withdraw success*\n" \
                      f"▪️[Transaction details (vitescan.io)]({explorer_url})"

        # Send tx confirmation to sender's private chat
        await self.gui.send_message(text=private_msg, chat_id=self.owner.id)

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
        await data['msg_confirmation'].edit_text(text=conf_msg, reply_markup=None, parse_mode=ParseMode.MARKDOWN)

        for i, receiver in enumerate(data['recipients']):
            # Consider anti-spam transaction lock
            if i > 0:
                time.sleep(settings.Tipbot.TIME_LOCK)

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
                await self.gui.send_message(text=msg, chat_id=self.owner.id)
                await self.gui.remove_state_messages(state)
                await query.answer()

                return

            # Remove messages from previous state only at first iteration
            if i == 0:
                # Show user notification/alert
                await self.gui.remove_state_messages(state)
                await query.answer(text='Transaction Confirmed!')
                time.sleep(1)

            # Create Vitescan.io explorer link to transaction
            transaction_hash = response['data']['hash']
            explorer_url = self.get_explorer_tx_url(transaction_hash)

            # Prepare user confirmation message
            amount = tools.float_to_str(data['amount'])
            private_msg = f"✅ Transaction sent successfully\n" \
                          f"▪️️ [Transaction details (vitescan.io)]({explorer_url})"
            receiver_msg = f"💸 `{amount} EPIC from ` {self.owner.get_mention()}"

            # Send tx confirmation to sender's private chat
            await self.gui.send_message(text=private_msg, chat_id=self.owner.id)

            # Send notification to receiver's private chat
            if not receiver.is_bot:
                await self.gui.send_message(text=receiver_msg, chat_id=receiver.id)

            # Finish send state when last element from list
            if i+1 == len(data['recipients']):
                await state.finish()
                await query.answer()

            logger.info(f"{self.owner.mention}: sent {amount} to {receiver.mention}")

            # Run threading process to update receiver balance (receiveTransactions call)
            logger.critical(f"ViteWallet::gui::send_tip() - start balance update for {receiver.mention}")
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
        if not payload['amount'] or float(payload['amount']) <= 0:
            return {'error': 1, 'msg': f"Wrong amount value.", 'data': None}

        # Iterate through list of receivers and send transaction to each
        for i, receiver in enumerate(payload['receivers']):
            # Respect anti-flood locking system
            if i > 0:
                await message.edit_text(text=f"{message.text} ({i+1}/{len(payload['receivers'])})")
                time.sleep(settings.Tipbot.TIME_LOCK)

            # Build and send tip transaction
            params = {
                'sender': payload['sender'].params(),
                'receiver': receiver.params(),
                'amount': payload['amount'],
                'type_of': 'tip',
                'network': settings.Network.VITE.symbol
                }

            logger.info(f"ViteWallet::send_tip() - sending tip: {params}")
            response = self._api_call('send_transaction', params, method='post', api_url=self.API_URL2)

            # Handle error from VITE network
            if response['error']:
                if 'sendBlock.Height must be larger than 1' in response['msg']:
                    msg = f"Your wallet is empty."
                else:
                    msg = f"{response['msg']}"
                finished_transactions.append({'error': 1, 'msg': msg, 'data': None})
            else:
                # Handle success transaction
                finished_transactions.append(response)
                success_transactions += 1

        return {'msg': f'send_tip success: {success_transactions}/{len(payload["receivers"])}',
                'error': 0, 'data': finished_transactions}


async def welcome_screen(user, message):
    active_chat = message.chat.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.HELP_STRING, parse_mode=ParseMode.MARKDOWN)

    if Tipbot.ADMIN_ID in str(user.id):
        await bot.send_media_group(chat_id=active_chat, media=media)
    else:
        await bot.send_media_group(chat_id=user.id, media=media)


async def faq_screen(user, message):
    active_chat = message.chat.id
    media = types.MediaGroup()
    media.attach_photo(types.InputFile('static/tipbot-wallet-gui.png'),
                       caption=Tipbot.FAQ_STRING, parse_mode=ParseMode.MARKDOWN)

    if Tipbot.ADMIN_ID in str(user.id):
        await bot.send_media_group(chat_id=active_chat, media=media)
    else:
        await bot.send_media_group(chat_id=user.id, media=media)

