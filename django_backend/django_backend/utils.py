from cryptography.fernet import Fernet

import json

from .secrets import secret_links_login, secret_links_key, encryption_key
from vtm.models import Token, TelegramUser
from .secret_links import OneTimeSecret
from .settings import VITEX_ADAPTER_SCRIPT_PATH
from .vite_adapter import ViteJsAdapter
from tipbot.models import Wallet


def get_or_create_telegram_user(request) -> tuple:
    """
    :param request: dict with request data (user details, session)
    :return: TelegramUser instance, created bool
    """
    payload = json.loads(request.body)
    exists = TelegramUser.objects.filter(id=payload['id'])

    # Handle creating new user, generate password
    if not exists:
        payload['password'] = TelegramUser.objects.make_random_password()
        request.session['acc_pass'] = payload['password']
        user = TelegramUser.objects.create_user(**payload)

    # Handle updating already existing user if needed
    else:
        exists.update(**payload)
        user = exists[0]

    return user, exists


def get_or_create_vite_token(payload: dict) -> Token:
    """
    :param payload: dict with request data (token details)
    :return: Token instance
    """
    token_data = {
        'id': payload['tokenId'],
        'name': payload['tokenName'],
        'symbol': payload['tokenSymbol'],
        'decimals': payload['decimals'],
        'max_supply': payload['maxSupply'],
        'total_supply': payload['totalSupply'],
        'owner_address': payload['owner']
        }
    token, created = Token.objects.get_or_create(
        id=payload['tokenId'], defaults=token_data)
    return token

def encrypt_mnemonics(mnemonics: str, enc_key: bytes = encryption_key):
    raw_mnemonics_string = mnemonics.lower()
    raw_mnemonics_bytes = bytes(raw_mnemonics_string, 'utf-8')
    encrypted_mnemonics_bytes = Fernet(enc_key).encrypt(raw_mnemonics_bytes)
    return encrypted_mnemonics_bytes.decode('utf-8')


def create_vite_wallet(user: TelegramUser) -> dict:
    """
    Communicate with back-end NodeJS Vite API and create new Vite wallet
    :param user: TelegramUser instance
    :return: JSON Response with Wallet instance
    """
    provider = ViteJsAdapter(script_path=VITEX_ADAPTER_SCRIPT_PATH)
    new_wallet = provider.create_wallet()

    if new_wallet['error']:
        response = {'error': 1, 'msg': new_wallet['msg'], 'data': None}
    else:
        # Encrypt mnemonics before storing in database
        encrypted_mnemonics_string = encrypt_mnemonics(new_wallet['data']['mnemonics'])

        if len(encrypted_mnemonics_string) < 292:
            response = {'error': 1, 'msg': 'Creating wallet error, please try again /create or contact @blacktyg3r', 'data': None}
        else:
            wallet = Wallet.objects.create(
                user=user,
                address=new_wallet['data']['address'],
                mnemonics=encrypted_mnemonics_string
                )
            response = {'error': 0, 'msg': 'wallet created successfully', 'data': wallet}

    return response


def create_secret_message(message: str):
    """Create a new secret message"""
    secret = OneTimeSecret(secret_links_login, secret_links_key)
    try:
        secret_obj = secret.share(message)
        secret_url = f"{secret.secret_link_url}{secret_obj['secret_key']}"
        return secret_url
    except Exception as e:
        print(e)
        return 'failed to create secret message'


def create_wallet_secret(wallet: Wallet, request) -> str:
    """
    :param wallet: Wallet instance
    :param request:
    :return: One-time use secret URL send to Telegram User with sensitive wallet data
    """

    if 'acc_pass' in request.session:
        password = request.session['acc_pass']
    else:
        password = TelegramUser.objects.make_random_password()
        wallet.user.set_password(password)
        wallet.user.save()

    print(password)

    message = f"\n// === EPIC-CASH TIPBOT === \\\\\n" \
              f"\n// WALLET MNEMONICS:\n" \
              f"\n{wallet.decrypt_mnemonics()}\n" \
              f"\n===========================" \
              f"\n// ACCOUNT PASSWORD:\n" \
              f"\n{password}" \
              f"\n===========================\n" \
              f"\nPlease make copy of this message, it can be viewed only once!"

    try:
        secret_url = create_secret_message(message)
        try: del request.session['acc_pass']
        except: pass
        return secret_url
    except Exception as e:
        print(e)
        return 'failed to create secret message'


def readable_balance(balance: dict):
    """Parse Vite API addressBalance to readable form"""
    epic_id = 'tti_f370fadb275bc2a1a839c753'

    if balance and 'balanceInfoMap' in balance.keys() \
        and epic_id in balance['balanceInfoMap'].keys():
        epic = balance['balanceInfoMap'][epic_id]
        as_int = int(epic['balance'])
        decimals = epic['tokenInfo']['decimals']
        return round((as_int / 10 ** decimals), 8)
    else:
        return 0.0


def is_valid_vite_address(address: str) -> bool:
    """Validate given address as valid Vite network address"""
    return len(address) == 55 and address.startswith('vite_')
