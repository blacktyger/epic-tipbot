from cryptography.fernet import Fernet
import requests

import json

from .secrets import secret_links_login, secret_links_key, encryption_key
from vtm.models import Token, TelegramUser
from .secret_links import OneTimeSecret
from tipbot.models import Wallet


def vite_api_call(query: str, params: dict) -> dict:
    """Handle Vite back-end API calls"""
    VITE_API = "http://localhost:3003"
    url = f"{VITE_API}/{query}/"

    try:
        response = requests.post(url=url, data=params)
    except Exception as e:
        print(e)
        return {'error': 1, 'msg': f"Connection problems, please try again later", 'data': None}

    if response.status_code == 200:
        response = response.json()

        if 'error' in response.keys():
            return {'error': 1, 'msg': response['error']['message'], 'data': None}
        else:
            return {'error': 0, 'msg': f'success _{query}_ call', 'data': response}
    else:
        return {'error': 1, 'msg': response.text, 'data': None}


def receive_transactions(wallet: Wallet):
    """
    Make receive call to Vite blockchain API in order to update balance
    :param wallet: Wallet model instance
    :return: None, background thread
    """
    params = {'mnemonics': wallet.decrypt_mnemonics()}
    balance = vite_api_call(query='balance', params=params)

    if not balance['error']:
        # Update receiver balance in database
        wallet.balance = balance['data']
        wallet.save()

    print(f"update thread finished.")


def get_or_create_telegram_user(request) -> tuple:
    """
    :param request: dict with request data (user details, session)
    :return: TelegramUser instance
    """
    payload = json.loads(request.body)
    exists = TelegramUser.objects.filter(id=payload['id'])

    # Make usernames always lowercase
    payload['username'] = payload['username'].lower()

    if not exists:
        payload['password'] = TelegramUser.objects.make_random_password()
        request.session['acc_pass'] = payload['password']
        user = TelegramUser.objects.create_user(**payload)
    else:
        user = TelegramUser.objects.get(**payload)

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


def create_wallet(user: TelegramUser) -> dict:
    """
    Communicate with back-end NodeJS Vite API and create new Vite wallet
    :param user: TelegramUser instance
    :return: JSON Response with Wallet instance
    """
    new_wallet = vite_api_call(query="create", params={})
    if new_wallet['error']:
        response = {'error': 1, 'msg': new_wallet['msg'], 'data': None}
    else:
        # Encrypt mnemonics before storing in database
        mnemonics_b = bytes(new_wallet['data']['mnemonics'], 'utf-8')
        encrypted_mnemonics = Fernet(encryption_key).encrypt(mnemonics_b)

        wallet = Wallet.objects.create(
            user=user,
            address=new_wallet['data']['address'],
            mnemonics=encrypted_mnemonics.decode('utf-8')
            )
        response = {'error': 0, 'msg': 'wallet created successfully', 'data': wallet}

    return response


def parse_vite_balance(data: dict):
    """Helper to parse Vite wallet balances from network"""
    balances = {}
    if 'balanceInfoMap' in data.keys():
        for token_id, token_details in data['balanceInfoMap'].items():
            token = get_or_create_vite_token(token_details['tokenInfo'])
            balance = int(token_details['balance']) / 10 ** token.decimals
            balances[token.symbol] = balance

    return {'error': 0, 'msg': 'balance success', 'data': balances}


def create_wallet_secret(wallet: Wallet, request) -> str:
    """
    :param wallet: Wallet instance
    :param request:
    :return: One-time use secret URL send to Telegram User with sensitive wallet data
    """
    message = f"\n// === EPIC-CASH TIPBOT === \\\\\n" \
              f"\n// WALLET MNEMONICS:\n" \
              f"\n{wallet.decrypt_mnemonics()}\n" \
              f"\n===========================" \
              f"\n// ACCOUNT PASSWORD:\n" \
              f"\n{request.session['acc_pass']}" \
              f"\n===========================\n" \
              f"\nPlease make copy of this message, it can be viewed only once!"

    secret = OneTimeSecret(secret_links_login, secret_links_key)
    secret_obj = secret.share(message)
    secret_url = f"{secret.secret_link_url}{secret_obj['secret_key']}"
    del request.session['acc_pass']

    return secret_url


def is_valid_vite_address(address: str) -> bool:
    """Validate given address as valid Vite network address"""
    return len(address) == 55 and address.startswith('vite_')