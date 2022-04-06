from django.http import JsonResponse
from rest_framework import viewsets
from django.db.models import Q

import threading
import json

from vtm.serializers import TelegramUserSerializer
from .serializers import WalletSerializer, TransactionSerializer
from vtm.models import Token, TelegramUser
from .models import Wallet, Transaction
from core import utils


epic_details = {
    'id': 'tti_f370fadb275bc2a1a839c753',
    'name': 'Epic Cash',
    'symbol': 'EPIC',
    'decimals': 8,
    'max_supply': '2100000 000000000',
    'total_supply': '890000000000000',
    'owner_address': 'vite_721a68f6ebd764e3f932832a05d87f8b1e8428393a0025bc72'
    }

epic, _ = Token.objects.get_or_create(**epic_details)


class WalletView(viewsets.ModelViewSet):
    serializer_class = WalletSerializer

    def get_queryset(self):
        queryset = Wallet.objects.all()
        wallet_address = self.request.query_params.get('address')
        print(wallet_address)
        if wallet_address:
            queryset = queryset.filter(address=wallet_address)
        return queryset


class TransactionView(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.all()
        username = self.request.query_params.get('username')
        user_id = self.request.query_params.get('user_id')
        address = self.request.query_params.get('address')

        if address:
            queryset = queryset.filter(Q(sender__address=address) | Q(address=address))
        if user_id:
            queryset = queryset.filter(Q(sender__user__id=user_id) | Q(receiver__user__id=user_id))
        if username:
            queryset = queryset.filter(Q(sender__user__username=username) | Q(receiver__user__username=username))

        return queryset.filter(status='success')


def send_transaction(request):
    """End-point for POST request with TelegramUser and Transaction data to send"""
    data = json.loads(request.body)
    receiver_wallet = None

    # // === VALIDATE PARAMS FOR TRANSACTION === \\
    # Handle Sender wallet from DB
    sender = TelegramUser.objects.filter(id=data['sender']['id']).first()

    # If no UserTelegram prompt that sender need to create account
    if not sender:
        response = {'error': 1, 'msg': f"sender have no account", 'data': None}
        return JsonResponse(response)

    sender_wallet = Wallet.objects.filter(user__id=data['sender']['id']).first()

    # If no Sender Wallet prompt warning
    if not sender_wallet:
        response = {'error': 1, 'msg': f"sender wallet not found", 'data': None}
        return JsonResponse(response)

    # Handle Receiver wallet from DB (if given)
    receiver_as_user = data['receiver']['username']

    if receiver_as_user:
        receiver = TelegramUser.objects.filter(username=receiver_as_user).first()

        # If no UserTelegram prompt that receiver need to create account
        if not receiver:
            response = {'error': 1, 'msg': f"receiver have no account.", 'data': None}
            return JsonResponse(response)

        # If no Receiver Wallet prompt warning
        receiver_wallet = Wallet.objects.filter(user=receiver).first()

        if not receiver_wallet:
            response = {'error': 1, 'msg': f"receiver wallet not found", 'data': None}
            return JsonResponse(response)

        address = receiver_wallet.address

    # If no receiver try to parse recipient address
    elif data['address']:
        address = data['address']

    else:
        response = {'error': 1, 'msg': f"invalid receiver or address", 'data': None}
        return JsonResponse(response)

    # If something wrong with amount
    if not data['amount']:
        response = {'error': 1, 'msg': f"invalid amount", 'data': None}
        return JsonResponse(response)
    # ========================================

    # // === SAVE AND SEND TRANSACTION === \\
    tx_params = {
        'sender': sender_wallet,
        'receiver': receiver_wallet,
        'address': address,
        'token': epic,
        'amount': data['amount']
        }

    tx = Transaction.objects.create(**tx_params)
    print(tx)

    # Prepare and send POST request to back-end Vite API
    tx_params = {
        'mnemonics': tx.sender.mnemonics,
        'toAddress': tx.prepare_address(),
        'tokenId': tx.token.id,
        'amount': tx.prepare_amount()
        }
    transaction = utils.vite_api_call(query='send_transaction', params=tx_params)

    # Update tx status and network transaction data:
    # if success save tx hash, else error msg.
    if not transaction['error']:
        tx.data = {'hash': transaction['data']['hash']}
        tx.status = 'success'
        tx.save()

        tx = TransactionSerializer(tx)
        payload = {'transaction': tx.data}

        if receiver_as_user:
            # Start thread to update receiver balance in background
            receiver_update = threading.Thread(target=utils.receive_transactions, args=[receiver_wallet])
            print(f"Starting update wallet {receiver_wallet} thread...")
            receiver_update.start()
            receiver_update.join()

            # Serialize TelegramUser instances
            receiver = TelegramUserSerializer(receiver)
            payload['receiver'] = receiver.data

        response = {'error': 0, 'msg': 'send success', 'data': payload}
    else:
        # Update transaction status in database and prepare failed response
        tx.status = 'failed'
        tx.data = {'error': transaction['msg']}
        tx.save()
        response = {'error': 1, 'msg': transaction['msg'], 'data': None}

    print('send_transaction: ', response['msg'])
    return JsonResponse(response)


def get_address(request):
    """End-point for POST request with TelegramUser data to retrieve wallet address"""
    response = {'error': 1, 'msg': 'Wallet does not exists', 'data': None}

    user = json.loads(request.body)
    wallet = Wallet.objects.filter(user__id=user['id']).first()

    if wallet:
        response = {'error': 0, 'msg': 'success _get_address_ call', 'data': wallet.address}

    return JsonResponse(response)


def get_balance(request):
    """
    End-point for POST request with TelegramUser
    data to retrieve wallet balance from network
    """
    response = {'error': 1, 'msg': 'invalid wallet', 'data': None}

    user = json.loads(request.body)
    wallet = Wallet.objects.filter(user__id=user['id']).first()

    if wallet:
        params = {'mnemonics': wallet.mnemonics}
        balance = utils.vite_api_call(query='balance', params=params)
        if not balance['error']:
            wallet.balance = balance['data']
            wallet.save()

            if wallet.balance['pendingTransactions']:
                response = {'error': 0, 'msg': 'Updating', 'data': 'Updating balance...'}
            else:
                response = utils.parse_vite_balance(balance['data'])
        else:
            print(balance['msg'])
            response = {'error': 1, 'msg': balance['msg'], 'data': None}

    print('get_balance: ', response['msg'])
    return JsonResponse(response)


def get_offline_balance(request):
    """
    End-point for POST request with TelegramUser
    data to retrieve wallet balance from DB (cached)
    """
    response = {'error': 1, 'msg': 'invalid wallet', 'data': None}
    user = json.loads(request.body)
    wallet = Wallet.objects.filter(user__id=user['id']).first()

    if wallet:
        wallet = WalletSerializer(wallet)
        response = {'error': 0, 'msg': 'Success', 'data': wallet.data}

    return JsonResponse(response)


# // -- Telegram User TIP-BOT Account Creation -- \\
# - User sends /create or /start command to BOT
# - BOT Python handler prepare data and send request
#   with user details (tg_id, tg_username) to Django BACK-END
# - Handle new and existing wallets
