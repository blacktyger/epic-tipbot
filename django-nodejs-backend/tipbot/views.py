from django.http import JsonResponse
from rest_framework import viewsets

import json

from .serializers import WalletSerializer, TransactionSerializer
from .models import Wallet, Transaction
from vtm.models import Token
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
        user_id = self.request.query_params.get('user_id')
        print(user_id)
        if user_id:
            queryset = queryset.filter(user__id=user_id)
        return queryset


def send_transaction(request):
    """End-point for POST request with TelegramUser and Transaction data to send"""
    data = json.loads(request.body)
    address = None
    receiver_wallet = None

    # Get Sender wallet from DB
    sender_wallet = Wallet.objects.filter(user__id=data['sender']['id']).first()

    # Try to get Receiver wallet from DB
    if data['receiver'] and not data['address']:
        receiver_wallet = Wallet.objects.filter(user__username=data['receiver']['username']).first()
        address = receiver_wallet.address

    # If no receiver try to parse recipient address
    if data['address'] and not data['receiver']:
        address = data['address']

    if address and data['amount']:
        # Prepare args to create new Transaction instance
        tx_params = {
            'sender': sender_wallet,
            'receiver': receiver_wallet,
            'address': address,
            'token': epic,
            'amount': data['amount']
            }

        tx = Transaction.objects.create(**tx_params)
        print(tx)

        # Prepare and send GET request to back-end Vite API
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
            response = {'error': 0, 'msg': 'Transaction sent successfully!', 'data': tx.data}
        else:
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
        response = {'error': 0, 'msg': 'Success get_address call', 'data': wallet.address}

    return JsonResponse(response)


def get_balance(request):
    """End-point for POST request with TelegramUser data to retrieve wallet balance"""
    response = {'error': 1, 'msg': 'Wallet does not exists', 'data': None}

    user = json.loads(request.body)
    wallet = Wallet.objects.filter(user__id=user['id']).first()
    params = {'mnemonics': wallet.mnemonics}

    if wallet:
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
            response = {'error': 1, 'msg': 'Connection errors, please try later.', 'data': None}

    print('get_balance: ', response['msg'])
    return JsonResponse(response)


# // -- Telegram User TIP-BOT Account Creation -- \\
# - User sends /create or /start command to BOT
# - BOT Python handler prepare data and send request
#   with user details (tg_id, tg_username) to Django BACK-END
# - Handle new and existing wallets
