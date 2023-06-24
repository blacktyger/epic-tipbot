""" "Graphical Interface" for EpicTipBot Wallet in Telegram chat window"""
from datetime import datetime, timedelta
import threading
import asyncio
import typing
import time

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageCantBeDeleted
from aiogram.dispatcher.filters.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram import types

from .. import logger, bot, tools, Tipbot
from ..wallet import AliasWallet
from .screens import *


# Wallet GUI buttons callback
wallet_cb = CallbackData('wallet', 'action', 'user', 'username')
donate_cb = CallbackData('donate', 'action', 'amount')
confirm_failed_tip_cb = CallbackData('failed_tip', 'action', 'user', 'message')

scheduler = AsyncIOScheduler()
scheduler.start()


# Manage Wallet GUI states
class WithdrawStates(StatesGroup):
    ask_for_address = State()
    ask_for_amount = State()
    confirmation = State()


class SendStates(StatesGroup):
    ask_for_recipient = State()
    ask_for_amount = State()
    confirmation = State()


class DonateStates(StatesGroup):
    ask_for_amount = State()
    confirmation = State()


class Interface:
    """
    Interface inside telegram chat to manage TipBot account.
    """

    def __init__(self, user):
        self.owner = user
        self.callback = CallbackData('wallet', 'action', 'user', 'username')

    async def new_wallet(self, payload):
        display_wallet = True

        # Handle error case
        if payload['error']:
            msg = f"🟡 {payload['msg']}"
            await self.send_message(text=msg, chat_id=self.owner.id)

        # Handle already activated account
        elif "already active" in payload['msg']:
            msg = f"🟢 Your account is already active :)"
            await self.send_message(text=msg, chat_id=self.owner.id)

        # Handle success creation
        else:
            display_wallet = False
            msg = new_wallet_string(payload)
            media = types.MediaGroup()
            media.attach_photo(types.InputFile('static/tipbot_v2_banner.png'),
                               caption=msg, parse_mode=ParseMode.HTML)
            await bot.send_media_group(media=media, chat_id=self.owner.id)

        if display_wallet: await self.show_wallet()

    async def show_wallet(self, state=None, message=None):
        """Spawn wallet interface inside Telegram chat window"""
        # Reset old state and data
        if state: await state.reset_state(with_data=True)

        # Prepare main wallet GUI (message and inline keyboard)
        keyboard = self.home_keyboard()

        # Handle users using commands in public chats without tip-bot account
        if not self.owner.is_registered:
            not_registered_msg = \
                f"👋 <b>Hey {self.owner.mention}</b>,\n\n" \
                f"First, create your 📲 <a href='https://t.me/EpicTipBot'><b>EpicTipBot</b></a> Account"

            kwargs = dict(text=not_registered_msg, chat_id=message.chat.id,
                          reply_to_message_id=message.message_id,
                          parse_mode=ParseMode.HTML,
                          disable_web_page_preview=True, message=message)

            await self.send_message(**kwargs)
            return

        # Handle account without wallet
        if not self.owner.wallet.address:
            # Display create wallet screen
            gui = no_wallet()
        else:
            # Display loading wallet GUI
            gui = loading_wallet_1()

        wallet_gui = await self.send_message(text=gui, chat_id=self.owner.id, reply_markup=keyboard)

        # Get wallet EPIC balance
        threading.Thread(target=self.owner.wallet.epic_balance).start()

        # Show animation of loading
        while self.owner.wallet.is_updating:
            await wallet_gui.edit_text(text=loading_wallet_2(),
                                       reply_markup=keyboard,
                                       parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.35)
            await wallet_gui.edit_text(text=loading_wallet_1(),
                                       reply_markup=keyboard,
                                       parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.35)

        balance = self.owner.wallet.last_balance

        # Handle response error
        if balance['error']:
            if 'database' in balance['msg'].lower():
                gui = connection_error_wallet()
            else:
                gui = invalid_wallet()

            # Update loading wallet GUI to error wallet
            await wallet_gui.edit_text(text=gui, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            logger.error(f"{self.owner.mention} interface::show_wallet() -> {balance['msg']}")
            return

        # Handle case when wallet needs to update new transactions
        pending_txs = int(balance['data']['pending'])

        if pending_txs:
            # Update wallet GUI with pending transactions number feedback
            logger.info(f"{self.owner.mention} pending transactions: {pending_txs}")
            await wallet_gui.edit_text(text=pending_2(pending_txs),
                                       reply_markup=keyboard,
                                       parse_mode=ParseMode.MARKDOWN)

            # Trigger the `receiveTransactions` vite api call
            thread = threading.Thread(target=self.owner.wallet.update_balance)
            thread.start()

            while self.owner.wallet.is_updating:
                await wallet_gui.edit_text(text=pending_1(pending_txs),
                                           reply_markup=keyboard,
                                           parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.7)
                await wallet_gui.edit_text(text=pending_2(pending_txs),
                                           reply_markup=keyboard,
                                           parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.7)

            balance = self.owner.wallet.epic_balance()

        # Prepare GUI strings
        epic_balance, balance_in_usd = balance['data']['string']
        wallet_gui_string = ready_wallet(epic_balance, balance_in_usd)

        # Update loading wallet GUI to ready wallet
        await wallet_gui.edit_text(text=wallet_gui_string,
                                   reply_markup=keyboard,
                                   parse_mode=ParseMode.MARKDOWN)

        logger.info(f"{self.owner.mention}: wallet GUI loaded")

    def get_receivers(self, message: types.Message) -> tuple:
        """
        Extract user mentions from tip message and return list of matching TipBotUser's
        :param message: types.Message (AIOGRAM)
        :return: tuple(registered_receivers, unknown_receivers)
        """
        registered_receivers = []
        unknown_receivers = []

        if len(message.entities) > 0:
            for user_mention in message.entities:
                if user_mention.type == 'mention':
                    start = user_mention.offset
                    stop = start + user_mention.length
                    username = message.text[start:stop].replace('@', '')
                    receiver = self.owner.from_dict({'username': username})

                    if receiver.is_registered:
                        logger.info(f"Wallet::get_tip_receivers() - registered_receiver by mention: {receiver}")
                        registered_receivers.append(receiver)
                    else:
                        logger.info(f"Wallet::get_tip_receivers() - unknown_receiver by mention: {receiver}")
                        unknown_receivers.append(receiver)

                elif user_mention['type'] == 'text_mention':
                    if user_mention.user:
                        receiver = self.owner.from_obj(user_mention.user)
                        if receiver.is_registered:
                            logger.info(
                                f"Wallet::get_tip_receivers() - registered_receiver by text_mention: {receiver}")
                            registered_receivers.append(receiver)
                        else:
                            logger.info(f"Wallet::get_tip_receivers() - unknown_receiver by text_mention: {receiver}")
                            unknown_receivers.append(receiver)

                elif user_mention['type'] == 'hashtag':
                    # Handle if receiver is an AccountAlias link
                    start = user_mention.offset
                    stop = start + user_mention.length
                    title = message.text[start:stop]
                    receiver = AliasWallet(title=title).get()

                    if receiver:
                        logger.info(f"Wallet::get_tip_receivers({title}) - parsed receiver from # alias: {receiver}")
                        registered_receivers.append(receiver)

            return registered_receivers, unknown_receivers

        else:
            # Try to parse receiver based on raw string
            try:
                match = message.parse_entities().split(' ')[1]
                print(match)

                if tools.is_int(match):
                    # Try to find user with given ID
                    receiver = self.owner.fom_dict({'id': tools.is_int(match)})

                    if receiver.is_registered:
                        logger.info(f"Wallet::get_tip_receivers({match}) - parsed receiver without mention: {receiver}")
                        registered_receivers.append(receiver)

                else:
                    # Try to find user with given @username
                    if match.startswith('@'):
                        receiver = self.owner.fom_dict({'username': match})

                        if receiver.is_registered:
                            logger.info(f"Wallet::get_tip_receivers({match}) - parsed receiver without mention: {receiver}")
                            registered_receivers.append(receiver)

            except Exception as e:
                logger.error(f'Error parsing receiver {e}')

        return registered_receivers, unknown_receivers

    @staticmethod
    def get_amount(message: types.Message) -> typing.Union[float, None]:
        """
        Parse amount from user's messages
        :param message: types.Message (AIOGRAM)
        :return: float or None
        """
        for match in message.text.split(' '):
            if tools.is_float(match):
                return tools.is_float(match)
            else:
                continue
        return None

    async def withdraw_1_of_3(self, state, query):
        # Set new state
        await WithdrawStates.ask_for_address.set()

        # Ask user for address
        ask_for_address = await query.message.reply(text='📩 Provide address to withdraw:',
                                                    reply=False, reply_markup=self.cancel_keyboard())
        # Save message to remove to temp storage
        await state.update_data(msg_ask_for_address=ask_for_address)
        await query.answer()

    async def withdraw_2_of_3(self, state, message):
        # Extract address from user message
        address = message.text.strip()

        # Validate withdraw address and save to storage
        if self.owner.wallet.is_valid_address(address):
            await state.update_data(address=address)

            # Remove messages from previous state
            await self.remove_state_messages(state)

            # Set new state
            await WithdrawStates.ask_for_amount.set()

            # Send message about amount
            ask_for_amount = await self.send_message(text='💵 How much to withdraw?',
                                                     chat_id=self.owner.id,
                                                     reply_markup=self.cancel_keyboard())
        else:
            # Remove messages from previous state
            await self.remove_state_messages(state)

            # Send invalid amount message
            ask_for_amount = await self.send_message(text='🔸 Invalid withdraw address, try again:',
                                                     chat_id=self.owner.id,
                                                     reply_markup=self.cancel_keyboard())

        # Save message to remove to temp storage
        await state.update_data(msg_ask_for_amount=ask_for_amount)

    async def withdraw_3_of_3(self, state, message):
        # Extract amount from user message
        amount = message.text.strip()

        try:
            # Validate and save amount
            amount = float(amount)
            await state.update_data(amount=amount)

            # Remove messages from previous state
            await self.remove_state_messages(state)

            # Set new state
            await WithdrawStates.confirmation.set()
            data = await state.get_data()
            amount = tools.float_to_str(data['amount'])

            confirmation_string = f" ☑️ Confirm your withdraw request:\n\n" \
                                  f"`▪️ Withdraw {amount} EPIC to:`\n" \
                                  f"`{data['address']}`\n"

            confirmation_keyboard = InlineKeyboardMarkup(one_time_keyboard=True)

            confirmation_keyboard.row(
                InlineKeyboardButton(text=f'✅ Confirm', callback_data='confirm_withdraw'),
                InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
                )

            # Send confirmation keyboard
            confirmation = await self.send_message(text=confirmation_string,
                                                   chat_id=self.owner.id,
                                                   reply_markup=confirmation_keyboard)

            # Save message to remove to temp storage
            await state.update_data(msg_confirmation=confirmation)

        except Exception as e:
            # Remove messages from previous state
            await self.remove_state_messages(state)
            logger.error(f"GUI::withdraw_3_of_3() - amount {e}")

            # Send wrong amount message
            confirmation = await self.send_message(text='🔸 Wrong amount, try again', chat_id=self.owner.id)

            # Save message to remove to temp storage
            await state.update_data(msg_confirmation=confirmation)

    async def send_to_user_1_of_3(self, state, query):
        # Set new state
        await SendStates.ask_for_recipient.set()

        # Ask user for recipient
        ask_for_recipient = await query.message.reply(text='📩 Provide receiver @username',
                                                      reply=False, reply_markup=self.cancel_keyboard())
        # Save message to remove to temp storage
        await state.update_data(msg_ask_for_recipient=ask_for_recipient)
        await query.answer()

    async def send_to_user_2_of_3(self, state, message):
        # Validate recipient and save to storage
        recipients, unknown = self.get_receivers(message)

        if recipients:
            await state.update_data(recipients=recipients)

            # Remove messages from previous state
            await self.remove_state_messages(state)

            # Set new state
            await SendStates.ask_for_amount.set()

            # Send message about amount
            ask_for_amount = await self.send_message(text='💵 How much to send?',
                                                     chat_id=self.owner.id,
                                                     reply_markup=self.cancel_keyboard())
        else:
            # Remove messages from previous state
            await self.remove_state_messages(state)

            # Send invalid amount message
            ask_for_amount = await self.send_message(text='🔸 Invalid recipient, try again:',
                                                     chat_id=self.owner.id,
                                                     reply_markup=self.cancel_keyboard())

        # Save message to remove to temp storage
        await state.update_data(msg_ask_for_amount=ask_for_amount)

    async def send_to_user_3_of_3(self, state, message):
        # Extract amount from user message
        amount = message.text.strip()

        try:
            # Validate and save amount
            amount = float(amount)
            await state.update_data(amount=amount)

            # Remove messages from previous state
            await self.remove_state_messages(state)

            # Set new state
            await SendStates.confirmation.set()
            data = await state.get_data()
            amount = tools.float_to_str(data['amount'])
            recipients = ', '.join([r.mention for r in data['recipients']])
            confirmation_string = f" ☑️ Confirm your send request:\n\n" \
                                  f"`▪️ Send {amount} EPIC to` " \
                                  f"`{recipients}`\n"

            confirmation_keyboard = InlineKeyboardMarkup(one_time_keyboard=True)

            confirmation_keyboard.row(
                InlineKeyboardButton(text=f'✅ Confirm', callback_data='confirm_send'),
                InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
                )

            # Send confirmation keyboard
            confirmation = await self.send_message(text=confirmation_string,
                                                   chat_id=self.owner.id,
                                                   reply_markup=confirmation_keyboard)

            # Save message to remove to temp storage
            await state.update_data(msg_confirmation=confirmation)

        except Exception as e:
            # Remove messages from previous state
            await self.remove_state_messages(state)
            logger.error(f"GUI::send_to_user_3_of_3() - amount {e}")

            # Send wrong amount message
            confirmation = await self.send_message(text='🔸 Wrong amount, try again', chat_id=self.owner.id)

            # Save message to remove to temp storage
            await state.update_data(msg_confirmation=confirmation)

    async def donate_1_of_2(self, state, query):
        # Set new state
        await DonateStates.ask_for_amount.set()

        # Send message about amount
        ask_for_amount = await self.send_message(text='💵 How much you would like to donate?',
                                                 chat_id=self.owner.id,
                                                 reply_markup=self.donate_keyboard())
        # Save message to remove to temp storage
        await state.update_data(msg_ask_for_amount=ask_for_amount)
        await query.answer()

    async def donate_2_of_2(self, state, query):
        amount = float(query.data.split('_')[1])
        await state.update_data(amount=amount)

        # Remove messages from previous state
        await self.remove_state_messages(state)

        # Set new state and provide donation address
        await DonateStates.confirmation.set()
        await state.update_data(address=Tipbot.DONATION_ADDRESS)

        data = await state.get_data()
        amount = tools.float_to_str(data['amount'])

        # Prepare confirmation string and keyboard
        confirmation_string = f" ☑️ Confirm your donation:\n\n" \
                              f"`▪️ Donate {amount} EPIC to developer`"

        confirmation_keyboard = InlineKeyboardMarkup(one_time_keyboard=True)
        confirmation_keyboard.row(
            InlineKeyboardButton(text=f'✅ Confirm', callback_data='confirm_withdraw'),
            InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
            )

        # Send confirmation keyboard
        confirmation = await self.send_message(text=confirmation_string,
                                               chat_id=self.owner.id,
                                               reply_markup=confirmation_keyboard)

        # Save message to remove to temp storage
        await state.update_data(msg_confirmation=confirmation)

    async def register_alias(self, message: types.Message):
        alias_title, address = message.text.split(' ')[1:3]

        try:
            details = eval(message.text.split('"')[1])
        except:
            details = {}

        # Handle owner
        owner = self.owner

        if 'owner' in details:
            owner_ = self.owner.from_dict({'username': details['owner'].replace('@', '')})
            if owner_.is_registered:
                owner = owner_

        # Create a new alias
        alias = AliasWallet(title=alias_title, owner=owner, address=address, details=details)

        # Update object params to database
        response = alias.register()

        try:
            # Handle error
            if response['error']:
                msg = f"🟡 Alias registration failed, {response['msg']}"
            else:
                msg = f"✅ Alias #{alias.title}:{alias.short_address()} created successfully!"
        except Exception as e:
            logger.error(f"main::create_account_alias() -> {str(e)}")
            msg = f"🟡 New alias registration failed."

        await self.send_message(text=msg, chat_id=message.chat.id, parse_mode=ParseMode.HTML)

    async def alias_details(self, message: types.Message):
        # Parse user text and prepare params
        cmd, alias_title = message.text.split(' ')

        # API call to database to get AccountAlias by #alias
        alias = AliasWallet(title=alias_title).get()

        if not alias: return

        balance = alias.balance()

        if balance:
            balance_, pending = tools.parse_vite_balance(balance)
        else:
            pending = 0
            balance_ = {'EPIC': 0}

        if 'owner' in alias.details:
            owner = alias.details['owner']
        else:
            owner = ''

        pending = f"  <code>{pending} pending tx</code>\n" if pending else ""
        title = f"🚦 #{alias.title}\n"
        separ = f"{'=' * len(title)}\n"
        value = f"💰  {tools.float_to_str(balance_['EPIC'])} EPIC\n"
        owner = f"👤  {owner}\n"
        link = f"➡️  {alias.details['url'].replace('https://', '')}" if 'url' in alias.details else ''

        msg = f"<b>{title}{separ}{value}</b>{pending}{owner}{link}"

        kwargs = dict(text=msg, chat_id=message.chat.id, parse_mode=ParseMode.HTML,
                      disable_web_page_preview=True)

        await self.send_message(**kwargs, message=message)

    async def send_tip_cmd(self, message):
        """
        Parse user tip command and prepare tip transaction data,
        manage user feedback during process
        :param message:
        :return:
        """
        fail_errors = 0
        active_chat = message.chat.id
        success_receivers = []

        # Remove potential double white space from message text
        message.text = message.text.replace('  ', ' ')

        # Parse receivers
        registered, unknown = self.get_receivers(message)

        print(registered, unknown)

        # Handle no receivers case, display feedback as self-delete message
        if not registered and not unknown:
            await self.tip_invalid_receiver_handler(message)
            return

        # Handle no registered receivers case, display feedback in active chat
        if unknown and not registered:
            await self.tip_no_receiver_handler(message)
            return

        # Handle case when tip command have wrong syntax
        if len(message.text.split(' ')) - (len(registered) + len(unknown)) != 2:
            logger.warning(f"@{self.owner.name} ViteWallet::gui::send_tip_cmd() - "
                           f"Wrong tip command syntax: '{message.text}'")
            return

        params = {
            'sender': self.owner,
            'receivers': registered,
            'amount': self.get_amount(message),
            }

        # Show that transaction is processed
        await self.delete_message(message)
        edited_message = await self.send_message(text=f"⌛️ {message.text}", chat_id=active_chat, message=message)

        # API Call to send tip transaction
        response = await self.owner.wallet.send_tip(params, edited_message)

        # Handle response error
        if response['error']:
            logger.error(f"@{self.owner.name} ViteWallet::gui::send_tip_cmd() - {response['msg']}")
            await self.send_message(text=f"🟡 {response['msg']}", chat_id=self.owner.id)
            await self.tip_error_handler(edited_message)
            return

        # Handle success tip transaction
        logger.info(f"@{self.owner.name} ViteWallet::gui::send_tip_cmd() - {response['msg']}")
        amount = tools.float_to_str(params['amount'])

        # Iterate trough receivers/transactions
        for i, tx in enumerate(response['data']):
            if tx['error']:
                # Send tx error to sender chat
                if not params['sender'].is_bot:
                    await self.send_message(text=f"🟡  {tx['msg']}", chat_id=params['sender'].id)

                    if not fail_errors:
                        await self.tip_error_handler(edited_message)
                        fail_errors += 1

            else:
                success_receivers.append(params['receivers'][i])
                explorer_url = self.owner.wallet.get_explorer_tx_url(tx['data']['hash'])
                private_msg = f"✅ `{amount} EPIC` to {params['receivers'][i].get_url()} \n" \
                              f"▪️️ [Tip details]({explorer_url})"
                receiver_msg = f"💸 `{amount} EPIC` from {params['sender'].get_url()}"

                # Send tx confirmation to sender's private chat
                if not params['sender'].is_bot:
                    await self.send_message(text=private_msg, chat_id=params['sender'].id)

                if not params['receivers'][i].is_bot:
                    # Send notification to receiver's private chat
                    await self.send_message(text=receiver_msg, chat_id=params['receivers'][i].id)

                    # Run threading process to update receiver balance (receiveTransactions call)
                    logger.warning(f"@{self.owner.name} ViteWallet::gui::send_tip() - "
                                   f"start balance update for {params['receivers'][i].mention}")
                    threading.Thread(target=params['receivers'][i].wallet.update_balance).start()

        # Finalize with final feedback
        if len(success_receivers) > 1:
            public_msg = f"🎉️ {params['sender'].get_url()} multi-tipped `{amount} EPIC` to:\n" \
                         f" {', '.join([receiver.get_url() for receiver in success_receivers])}"
        elif len(success_receivers) > 0:
            public_msg = f"❤️ {params['sender'].get_url()} tipped " \
                         f"`{amount} EPIC` to {params['receivers'][0].get_url()}"
        else:
            public_msg = f""

        # Remove sender /tip message
        try:
            await self.delete_message(edited_message)
        except:
            pass

        # Send notification with tip confirmation in active channel
        await self.send_message(text=public_msg, chat_id=active_chat, message=message)

    async def maintenance(self, message):
        msg = f"⚙️ ⚠️ @EpicTipBot is under a maintenance, you will get notice via DM when " \
              f"bot will be back online, apologies for inconvenience."

        kwargs = dict(text=msg, disable_web_page_preview=True,
                      reply_markup=self.confirm_failed_tip_keyboard(),
                      parse_mode=ParseMode.HTML, chat_id=message.chat.id, message=message)

        await self.send_message(**kwargs)

        self.auto_delete(message, 20)

    async def spam_message(self, message, send_wallet=False):
        msg = message.text.split('"')[1]
        confirm = message.text.split('"')[-1]
        print(msg, confirm)

        button = KeyboardButton('/wallet')
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(button)

        if self.owner.id == int(Tipbot.ADMIN_ID):
            users = self.owner.get_users(100)

            users = [user['id'] for user in users]
            print(f"Got {len(users)} ID's from DB")
            print(users)
            if 'yes' not in confirm:
                users = [self.owner.id]

            for user_id in users:
                user = self.owner.from_dict({'id': user_id})
                success = await self.send_message(text=msg, chat_id=user.id, reply_markup=keyboard)
                if success:
                    logger.critical(f"{user} spam message sent success")
                    if send_wallet:
                        await user.ui.show_wallet()
                time.sleep(0.3)

    def auto_delete(self, message, delta):
        """Add job to scheduler with time in seconds from now to run the task"""
        date = datetime.now() + timedelta(seconds=delta)
        scheduler.add_job(self.delete_message, "date", run_date=date, kwargs={"message": message})

    async def tip_invalid_receiver_handler(self, message):
        await self.delete_message(message)
        no_receiver_msg = f"💬️ {self.owner.mention}, {' '.join(message.text.split(' ')[1:-1])} is not a valid receiver."

        kwargs = dict(text=no_receiver_msg, chat_id=message.chat.id,
                      parse_mode=ParseMode.HTML,
                      reply_markup=self.confirm_failed_tip_keyboard(),
                      disable_web_page_preview=True, message=message)

        warning_message = await self.send_message(**kwargs)

        self.auto_delete(warning_message, 30)

    async def tip_no_receiver_handler(self, message: types.Message):
        await self.delete_message(message)
        no_receiver_msg = f"👋 <b>Hey {message.text.split(' ')[1]}</b>,\n" \
                          f"{self.owner.mention} is trying to tip you!\n\n" \
                          f" <b>Create your 📲 <a href='https://t.me/EpicTipBot'>EpicTipBot</a> Account</b>"

        kwargs = dict(text=no_receiver_msg, chat_id=message.chat.id,
                      parse_mode=ParseMode.HTML, message=message)

        await self.send_message(**kwargs)

    async def tip_error_handler(self, message):
        await self.delete_message(message)
        public_feedback = f"💬️ {self.owner.mention}, there was problem with your tip \n\n" \
                          f" <b>Visit 📲 <a href='https://t.me/EpicTipBot'>Wallet App</a></b>"

        kwargs = dict(text=public_feedback,
                      reply_markup=self.confirm_failed_tip_keyboard(),
                      parse_mode=ParseMode.HTML, chat_id=message.chat.id, message=message)

        await self.send_message(**kwargs)

    def home_keyboard(self) -> InlineKeyboardMarkup:
        """
        Prepare Wallet GUI InlineKeyboard
        :return: InlineKeyboardMarkup instance (aiogram)
        """

        buttons = ['deposit', 'withdraw', 'send', 'donate', 'support']
        icons = ['↘ ', '↗️ ', '➡️ ', '❤️ ', '💬️ ']

        buttons = [InlineKeyboardButton(
            text=f"{icons[i]}{btn.capitalize()}", callback_data=self.callback.new(
                action=btn, user=self.owner.id, username=self.owner.name))
            for i, btn in enumerate(buttons)]

        keyboard_inline = InlineKeyboardMarkup() \
            .row(buttons[0], buttons[1]) \
            .row(buttons[2], buttons[3]) \
            .add(buttons[4])

        return keyboard_inline

    def confirm_failed_tip_keyboard(self):
        # """Initialize InlineKeyboard to cancel operation/state"""
        keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(InlineKeyboardButton(
            text='☑️️  Confirm',
            callback_data=self.callback.new(
                action='confirm_failed_tip',
                user=self.owner.id,
                username='')
            )
            )

        return keyboard

    @staticmethod
    def cancel_keyboard():
        """Initialize InlineKeyboard to cancel operation/state"""
        keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
        keyboard.add(button)

        return keyboard

    @staticmethod
    def donate_keyboard():
        """Initialize InlineKeyboard for donate operation"""
        keyboard = InlineKeyboardMarkup()
        donate_1 = InlineKeyboardButton(text='1 EPIC', callback_data='donate_1')
        donate_5 = InlineKeyboardButton(text='5 EPIC', callback_data='donate_5')
        donate_10 = InlineKeyboardButton(text='10 EPIC', callback_data='donate_10')
        button = InlineKeyboardButton(text='✖️ Cancel', callback_data='cancel_any')
        keyboard.row(donate_1, donate_5, donate_10).add(button)

        return keyboard

    # async def gui_button(self, ):
    #     keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    #     keyboard.add(KeyboardButton(text='✖️ Cancel', callback_data='cancel_any'))
    #     await self.send_message(text='.', chat_id=self.owner.id, reply_markup=keyboard)

    async def cancel_state(self, state, query):
        # Remove messages
        await self.remove_state_messages(state)

        # Reset state
        logger.info(f"{self.owner.username}: Reset state ({await state.get_state()}) and data")
        await state.reset_state(with_data=True)
        await query.answer()

    async def show_support(self, query):
        msg = f'🔘 Please join **@EpicTipBotSupport**'
        await self.send_message(text=msg, chat_id=self.owner.id)
        await query.answer()

    @staticmethod
    async def send_message(**kwargs):
        """Helper function for sending messages from bot to TelegramUser"""
        kwargs['parse_mode'] = kwargs['parse_mode'] \
            if 'parse_mode' in kwargs else ParseMode.MARKDOWN

        if 'disable_web_page_preview' not in kwargs:
            kwargs['disable_web_page_preview'] = True

        # If there is Message objects in kwargs, extract topic thread ID to reply in to it
        if 'message' in kwargs:
            if kwargs['message'].chat.is_forum:
                kwargs['reply_to_message_id'] = kwargs['message'].message_thread_id
            kwargs.pop('message')

        try:
            message = await bot.send_message(**kwargs)
            return message

        except Exception as e:
            # Change parse mode to HTML and try again
            logger.warning(f"{e} (chat_id: {kwargs['chat_id']})")
            kwargs['parse_mode'] = ParseMode.HTML

            try:
                message = await bot.send_message(**kwargs)
                return message

            except Exception as ee:
                logger.warning(f"{ee} (chat_id: {kwargs['chat_id']})")

    @staticmethod
    async def delete_message(message: types.Message):
        """
        Wrapper function with try, except block
        around removing TelegramMessages
        """
        try:
            await message.delete()
        except (MessageToDeleteNotFound, MessageCantBeDeleted) as e:
            logger.warning(f"{message.from_user.mention}: {e}")
            pass

    async def remove_state_messages(self, state: FSMContext):
        """Remove bot messages saved in temp storage"""
        state_ = await state.get_state()

        if state_:
            data = await state.get_data()

            # Remove messages
            if f'msg_{state_.split(":")[-1]}' in data.keys():
                msg = data[f'msg_{state_.split(":")[-1]}']
                try:
                    logger.info(f"DELETE MSG: {msg['id']}")
                except Exception:
                    pass

                await self.delete_message(msg)
