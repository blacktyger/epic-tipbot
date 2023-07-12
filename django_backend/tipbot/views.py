import decimal
import json

from django.views.generic import CreateView
from django.http import JsonResponse
from rest_framework import viewsets
from django.db.models import Q

from .serializers import WalletSerializer, AccountAliasSerializer, EpicTransactionSerializer, ViteTransactionSerializer
from .models import Wallet, Transaction, AccountAlias, ListenerPort, Coin
from django_backend.settings import VITEX_ADAPTER_SCRIPT_PATH
from django_backend.vite_adapter import ViteJsAdapter
from django_backend.logger_ import get_logger
from vtm.models import Token, TelegramUser
from django_backend import utils


logger = get_logger()

epic_token = {
    'id': 'tti_f370fadb275bc2a1a839c753',
    'name': 'Epic Cash',
    'symbol': 'EPIC',
    'decimals': 8,
    'max_supply': '2100000 000000000',
    'total_supply': '890000000000000',
    'owner_address': 'vite_721a68f6ebd764e3f932832a05d87f8b1e8428393a0025bc72'
    }

epic_token, _ = Token.objects.get_or_create(**epic_token)
epic_coin, _ = Coin.objects.get_or_create()

class WalletView(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        queryset = Wallet.objects.all()
        print(self.request.query_params)

        if wallet_user := self.request.query_params.get('user'):
            queryset = queryset.filter(Q(user__id=wallet_user) | Q(user__username__iexact=wallet_user), network=wallet_network)
        if wallet_network := self.request.query_params.get('network'):
            queryset = queryset.filter(network=wallet_network)
        if wallet_address := self.request.query_params.get('address'):
            queryset = queryset.filter(address=wallet_address, network=wallet_network)

        return queryset


def save_wallet(request):
    """Save EpicTipBot native chain wallets details in to db"""
    if request.method == 'POST':
        payload = json.loads(request.body.decode('utf-8'))
        user = TelegramUser.objects.get(id=payload['user']['id'])
        encrypted_mnemonics = utils.encrypt_mnemonics(payload['mnemonics'])
        wallet = Wallet.objects.create(user=user, network=payload['network'], address=payload['address'], mnemonics=encrypted_mnemonics)

        return JsonResponse({'error': 0, 'msg': 'wallet created successfully', 'data': wallet.address})


class TransactionView(viewsets.ModelViewSet):
    serializer_class = EpicTransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.all()
        print(self.request.query_params)

        if type_of := self.request.query_params.get('type_of'):
            queryset = queryset.filter(type_of=type_of)
        if network := self.request.query_params.get('network'):
            queryset = queryset.filter(network=network)
        if id := self.request.query_params.get('id'):
            queryset = queryset.filter(Q(sender__user__id=id) | Q(receiver__user__id=id))
        if address := self.request.query_params.get('address'):
            queryset = queryset.filter(Q(sender__address=address) | Q(address=address))
        if username := self.request.query_params.get('username'):
            queryset = queryset.filter(Q(sender__user__username__iexact=username) | Q(receiver__user__username__ieaxact=username))
        if tx_slate_id := self.request.query_params.get('tx_slate_id'):
            queryset = queryset.filter(data__id=tx_slate_id)

        logger.info(f"{[x for x in [id, address, username, tx_slate_id] if x]}: get_transactions api call")
        return queryset.filter(Q(status='success') | Q(status='pending'))


def save_epic_transaction(request):
    if request.method == 'POST':
        payload = json.loads(request.body.decode('utf-8'))
        print(payload)

        if payload['type_of'] != 'deposit':
            sender = TelegramUser.objects.filter(id=payload['sender']['id']).first()
            sender_wallet = sender.wallet.filter(network=payload['network']).first()
        else:
            sender_wallet = None

        tx_params = {
            'coin': epic_coin,
            'data': payload['data'],
            'sender': sender_wallet,
            'status': payload['status'],
            'amount': decimal.Decimal(payload['amount']),
            'type_of': payload['type_of'],
            'network': payload['network'],
            'message': payload['message'],
            }

        # Handle withdraw or fee transaction (address as receiver)
        if 'withdraw' in payload['type_of'] or 'fee' in payload['type_of']:
            tx_params.update({'address': payload['address']})

        # Handle send transaction (TipBotUser as receiver)
        elif payload['type_of'] == 'send' or payload['type_of'] == 'tip' or payload['type_of'] == 'deposit':
            if 'address' in payload['receiver']:
                tx_params.update({'address': payload['receiver']['address']})
            else:
                receiver = TelegramUser.objects.filter(id=payload['receiver']['id']).first()
                tx_params.update({'receiver': receiver.wallet.filter(network=payload['network']).first()})

        # Create and save Transaction to database
        tx = Transaction.objects.create(**tx_params)
        tx = EpicTransactionSerializer(tx)

        response = {'error': 0, 'msg': 'tx successfully saved', 'data': tx.data}
        return JsonResponse(response)


def update_epic_transaction(request):
    if request.method == 'POST':
        payload = json.loads(request.body.decode('utf-8'))
        print(payload)

        if 'tx_slate_id' in payload:
            if transaction := Transaction.objects.filter(data__id=payload['tx_slate_id']).first():
                if 'data' in payload:
                    transaction.data = payload['data']

                transaction.status = payload['status']
                transaction.save()
                response = {'error': 0, 'msg': 'tx successfully updated', 'data': EpicTransactionSerializer(transaction).data}
            else:
                response = {'error': 1, 'msg': f"failed to get tx with id {payload['tx_slate_id']}", 'data': None}

        elif 'outgoing_tx_slate_id' in payload:
            if transaction := Transaction.objects.filter(data__outgoing_tx__id=payload['outgoing_tx_slate_id']).first():
                transaction.status = payload['status']
                transaction.save()
                response = {'error': 0, 'msg': 'tx successfully updated', 'data': EpicTransactionSerializer(transaction).data}
            else:
                response = {'error': 1, 'msg': f"failed to get outgoing tx with id {payload['outgoing_tx_slate_id']}", 'data': None}
        else:
            response = {'error': 1, 'msg': f" 'tx_slate_id' or 'outgoing_tx_slate_id' not provided", 'data': None}

        return JsonResponse(response)


def send_transaction(request):
    """
    End-point for POST request with TelegramUser and Transaction data to send
    """
    data = json.loads(request.body)
    sender = TelegramUser.objects.filter(id=data['sender']['id']).first()
    sender_wallet = sender.wallet.filter(network=data['network']).first()

    # Prevent accidental multiple transactions
    if sender.locked:
        # Ignore locking for fee transactions
        if data['type_of'] != 'fee':
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
        'token': epic_token,
        'amount': decimal.Decimal(data['amount']),
        'type_of': data['type_of'],
        'network': data['network']
        }

    # Handle withdraw or fee transaction (address as receiver)
    if 'withdraw' in data['type_of'] or 'fee' in data['type_of']:
        tx_params.update({'address': data['address']})

    # Handle send transaction (TipBotUser as receiver)
    elif 'send' in data['type_of'] or 'tip' in data['type_of']:
        if 'address' in data['receiver']:
            tx_params.update({'address': data['receiver']['address']})
        else:
            receiver = TelegramUser.objects.filter(id=data['receiver']['id']).first()
            tx_params.update({'receiver': receiver.wallet.filter(network=data['network']).first()})

    # Create and save Transaction to database
    tx = Transaction.objects.create(**tx_params)

    # Prepare and execute back-end Vite.js script
    tx_params = {
        'mnemonics': tx.sender.decrypt_mnemonics(),
        'address_id': 0,
        'to_address': tx.prepare_address(),
        'token_id': tx.token.id,
        'amount': tx.prepare_amount()
        }

    provider = ViteJsAdapter(logger=logger, script_path=VITEX_ADAPTER_SCRIPT_PATH)
    transaction = provider.send_transaction(**tx_params)

    # Update tx status and network transaction data:
    # if success save tx hash, else error msg.
    if not transaction['error']:
        tx.data = {'hash': transaction['data']['hash']}
        tx.status = 'success'
        tx.save()
        logger.info(f"tipbot::views::send_transaction() - {tx}")

        # Lock account to prevent spam/unwanted transactions
        sender.temp_lock()

        tx = ViteTransactionSerializer(tx)
        response = {'error': 0, 'msg': 'send success', 'data': tx.data['data']}

    else:
        # Update transaction status in database and prepare failed response
        tx.status = 'failed'
        tx.data = {'error': transaction['msg']}
        tx.save()
        response = {'error': 1, 'msg': transaction['msg'], 'data': None}
        logger.warning(f"tipbot::views::send_transaction() - {response['msg']}")

    return JsonResponse(response)


def get_address(request):
    """
    End-point for POST request with TelegramUser data to retrieve wallet address
    """
    payload = json.loads(request.body)

    if wallet := Wallet.objects.filter(user__id=payload['id'], network=payload['network']).first():
        response = {'error': 0, 'msg': f'get_address success', 'data': wallet.address}
    else:
        response = {'error': 1, 'msg': 'Wallet does not exists', 'data': None}

    return JsonResponse(response)


def update(request):
    """
    End-point for POST request to receive wallet pendingTransactions
    """
    payload = json.loads(request.body)

    # Used to update non EpicTipBot wallets, requires mnemonics and address derivation id
    if 'external_wallet' in payload:
        params = {'mnemonics': payload['mnemonics'], 'address_id': payload['address_id'] if 'address_id' in payload else 0}
        provider = ViteJsAdapter(logger=logger, script_path=VITEX_ADAPTER_SCRIPT_PATH)
        provider.get_updates(**params)
        return JsonResponse(provider.response)

    logger.info(f"tipbot::views::get_update_balance({payload})")
    if wallet := Wallet.objects.filter(Q(user__id=payload['id']) | Q(address=payload['address']), network=payload['network']).first():
        params = {'mnemonics': wallet.decrypt_mnemonics(), 'address_id': 0}
        provider = ViteJsAdapter(logger=logger, script_path=VITEX_ADAPTER_SCRIPT_PATH)
        provider.get_updates(**params)
    else:
        return JsonResponse({'error': 1, 'msg': 'invalid wallet', 'data': None})

    return JsonResponse(provider.response)


def get_mnemonics(request):
    """
    End-point for POST request to Request wallet mnemonic seed phrase via OneTimeSecret Link
    """
    payload = json.loads(request.body)
    logger.info(f"tipbot::views::get_mnemonics({payload})")

    if wallet := Wallet.objects.filter(user__id=payload['user']['id'], network=payload['network']).first():
        secret_link = utils.create_secret_message(message=wallet.decrypt_mnemonics())
        response = {'error': 0, 'msg': f'get_mnemonics success', 'data': secret_link}
    else:
        response = {'error': 1, 'msg': 'Wallet does not exists', 'data': None}

    return JsonResponse(response)


def get_balance(request):
    """
    End-point for POST request with TelegramUser data to retrieve wallet balance from network
    """
    payload = json.loads(request.body)
    logger.info(f"tipbot::views::get_balance({payload})")

    if 'id' in payload:
        wallet = Wallet.objects.filter(user__id=payload['id'], network=payload['network']).first()
    elif 'address' in payload:
        wallet = Wallet.objects.filter(address=payload['address'], network=payload['network']).first()
    else:
        wallet = None

    if wallet:
        params = {'address': wallet.address}
    elif not wallet and 'address' in payload:
        params = {'address': payload['address']}
    else:
        response = {'error': 1, 'msg': 'invalid wallet', 'data': None}
        return JsonResponse(response)

    provider = ViteJsAdapter(logger=logger, script_path=VITEX_ADAPTER_SCRIPT_PATH)
    provider.get_balance(**params)

    if provider.response['error']:
        return JsonResponse(provider.response)

    if wallet:
        wallet.balance = provider.response['data']
        wallet.save()

    response = {'error': 0, 'msg': 'success', 'data': provider.response['data']}
    return JsonResponse(response)


class AccountAliasCreateView(CreateView):
    model = AccountAlias
    fields = '__all__'

    def post(self, request, *args, **kwargs):
        payload = json.loads(request.body)
        print(payload)

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


def ports(request):
    if request.method == 'GET':
        if port_ := request.GET.get('port', None):
            port = ListenerPort.objects.filter(port=port_).first()

            if port:
                response = {'error': 0, 'msg': 'success', 'data': port.port}
            else:
                response = {'error': 1, 'msg': f'invalid port: {port_}', 'data': None}
        else:
            response = {'error': 1, 'msg': f'invalid port: {port_}', 'data': None}

        return JsonResponse(response)

    if request.method == 'POST':
        payload = json.loads(request.body)

        port, created = ListenerPort.objects.get_or_create(port=payload['port'])

        if not created:
            response = {'error': 1, 'msg': f'{port} already exists', 'data': None}
        else:
            if 'data' in payload:
                port.data = payload['data']
                port.save()
            response = {'error': 0, 'msg': f'{port} added', 'data': port.port}

        return JsonResponse(response)
