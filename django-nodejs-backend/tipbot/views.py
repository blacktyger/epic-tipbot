from django.views.generic import CreateView
from django.http import JsonResponse
from rest_framework import viewsets
from django.db.models import Q

import json

from .serializers import WalletSerializer, TransactionSerializer, AccountAliasSerializer
from core.js_handler import execute_node_call, send, update_
from vtm.models import Token, TelegramUser
from .models import Wallet, Transaction, AccountAlias
from core.logger_ import setup_logging
from core import utils, js_handler


logger = setup_logging(name=__name__, console_log_output="stdout", console_log_level="info", console_log_color=True,
                       logfile_file=__name__ + ".log", logfile_log_level="info", logfile_log_color=False,
                       log_line_template="%(color_on)s[%(asctime)s] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s")

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
        wallet_user = self.request.query_params.get('user')
        wallet_address = self.request.query_params.get('address')
        wallet_network = self.request.query_params.get('network')

        if wallet_user:
            queryset = queryset.filter(Q(user__id=wallet_user) |
                                       Q(user__username__iexact=wallet_user))
        if wallet_address:
            queryset = queryset.filter(address=wallet_address)

        if wallet_network:
            queryset = queryset.filter(network=wallet_network)

        return queryset


class AccountAliasView(viewsets.ModelViewSet):
    serializer_class = AccountAliasSerializer

    def get_queryset(self):
        queryset = AccountAlias.objects.all()
        address = self.request.query_params.get('address')
        title = self.request.query_params.get('title')

        if address:
            queryset = queryset.filter(address=address)

        if title:
            queryset = queryset.filter(title__iexact=title)

        return queryset


class TransactionView(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.all()

        id = self.request.query_params.get('id')
        address = self.request.query_params.get('address')
        username = self.request.query_params.get('username')

        if address:
            queryset = queryset.filter(Q(sender__address=address) | Q(address=address))
        if id:
            queryset = queryset.filter(Q(sender__user__id=id) | Q(receiver__user__id=id))
        if username:
            queryset = queryset.filter(Q(sender__user__username__iexact=username) |
                                       Q(receiver__user__username__ieaxact=username))

        logger.info(f"[{username, id, address}]: get_transactions api call")
        return queryset.filter(status='success')


class AccountAliasCreateView(CreateView):
    model = AccountAlias
    fields = '__all__'

    def post(self, request, *args, **kwargs):
        payload = json.loads(request.body)

        # Get owner TelegramUser object
        owner = TelegramUser.objects.filter(id=payload['owner']).first()

        if owner:
            payload['owner'] = owner
            alias, created = self.model.objects.update_or_create(title=payload['title'], defaults=payload)
            serialized = AccountAliasSerializer(alias)

            if not created:
                response = {'error': 1, 'msg': 'alias already active', 'data': serialized.data}
            else:
                response = {'error': 0, 'msg': 'alias registration success', 'data': serialized.data}
        else:
            response = {'error': 1, 'msg': 'Only @EpicTipBot User can create aliases.', 'data': None}

        return JsonResponse(response)


def send_transaction(request):
    """
    End-point for POST request with TelegramUser and Transaction data to send
    """
    data = json.loads(request.body)
    sender = TelegramUser.objects.filter(id=data['sender']['id']).first()
    sender_wallet = sender.wallet.first()

    # Prevent accidental multiple transactions
    if sender.locked:
        response = {'error': 1, 'msg': f"Too many transactions, please wait 5 seconds.", 'data': None}
        # logger.error(f"[{data['sender']}]: {response['msg']}")
        return JsonResponse(response)

    # If something is wrong with the amount
    if not data['amount']:
        response = {'error': 1, 'msg': f"invalid amount", 'data': None}
        # logger.error(f"[{sender}]: {response['msg']}")
        return JsonResponse(response)

    tx_params = {
        'sender': sender_wallet,
        'token': epic,
        'amount': data['amount'],
        'type_of': data['type_of'],
        'network': data['network']
        }

    # Handle withdraw transaction (address as receiver)
    if 'withdraw' in data['type_of']:
        tx_params.update({'address': data['address']})

    # Handle send transaction (TipBotUser as receiver)
    elif 'send' in data['type_of'] or 'tip' in data['type_of']:
        if 'address' in data['receiver'].keys():
            tx_params.update({'address': data['receiver']['address']})
        else:
            receiver = TelegramUser.objects.filter(id=data['receiver']['id']).first()
            tx_params.update({'receiver': receiver.wallet.first()})

    # Create and save Transaction to database
    tx = Transaction.objects.create(**tx_params)

    # Prepare and execute back-end Vite.js script
    tx_params = {
        'mnemonics': tx.sender.decrypt_mnemonics(),
        'toAddress': tx.prepare_address(),
        'tokenId': tx.token.id,
        'amount': tx.prepare_amount()
        }
    transaction = send(**tx_params)

    # Update tx status and network transaction data:
    # if success save tx hash, else error msg.
    if not transaction['error']:
        tx.data = {'hash': transaction['data']['hash']}
        tx.status = 'success'
        tx.save()
        logger.info(f"tipbot::views::send_transaction() - {tx}")

        # Lock account to prevent spam/unwanted transactions
        sender.temp_lock()

        tx = TransactionSerializer(tx)
        response = {'error': 0, 'msg': 'send success', 'data': tx.data['data']}

    else:
        # Update transaction status in database and prepare failed response
        tx.status = 'failed'
        tx.data = {'error': transaction['msg']}
        tx.save()
        response = {'error': 1, 'msg': transaction['msg'], 'data': None}
        logger.error(f"tipbot::views::send_transaction() - {response['msg']}")

    return JsonResponse(response)


def get_address(request):
    """
        End-point for POST request with TelegramUser
        data to retrieve wallet address
        """
    response = {'error': 1, 'msg': 'Wallet does not exists', 'data': None}

    user = json.loads(request.body)
    wallet = Wallet.objects.filter(user__id=user['id']).first()

    if wallet:
        response = {'error': 0, 'msg': f'[{wallet}] success _get_address_ call', 'data': wallet.address}
        logger.info(f"[{wallet.user}]: {response['msg']}")

    return JsonResponse(response)


def update(request):
    """
    End-point for POST request with TelegramUser
    data to receive wallet pendingTransactions
    """
    payload = json.loads(request.body)
    logger.info(f"tipbot::views::get_update_balance({payload})")

    wallet = Wallet.objects.filter(Q(user__id=payload['id']) |
                                   Q(address=payload['address'])).first()
    response = {'error': 1, 'msg': 'invalid wallet', 'data': None}

    if not wallet: return JsonResponse(response)

    # Set timeout to get 10sec for each pending tx to avoid timeout issues
    timeout = payload['num'] * 10
    update_(mnemonics=wallet.decrypt_mnemonics(), timeout=timeout)
    response = {'error': 0, 'msg': 'success update', 'data': None}

    # if '[object Object]' in response['msg']:

    return JsonResponse(response)


def get_balance(request):
    """
    End-point for POST request with TelegramUser
    data to retrieve wallet balance from network
    """
    response = {'error': 1, 'msg': 'invalid wallet', 'data': None}

    payload = json.loads(request.body)
    logger.info(f"tipbot::views::get_balance({payload})")

    wallet = Wallet.objects.filter(Q(user__id=payload['id']) |
                                   Q(address=payload['address'])).first()

    if not wallet: return JsonResponse(response)

    balance = execute_node_call(func='balance', mnemonics=wallet.decrypt_mnemonics())

    if balance['error']: return JsonResponse(balance)

    wallet.balance = balance['data']
    wallet.save()
    response = {'error': 0, 'msg': 'success', 'data': wallet.balance}

    return JsonResponse(response)


def get_address_balance(request):
    """
    End-point for POST request with address
    data to retrieve account balance from network
    """
    payload = json.loads(request.body)
    logger.info(f"tipbot::views::get_address_balance({payload})")
    response = js_handler.address_balance(payload['address'])

    if response['error']: return JsonResponse(response)

    response['data'] = utils.readable_balance(response['data'])

    return JsonResponse(response)