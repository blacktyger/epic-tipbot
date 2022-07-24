import concurrent.futures
import subprocess
import json


def balance(**kwargs):
    mnemonics = kwargs['mnemonics']
    try:
        response = subprocess.run(
            ['node', 'static/src/js/api_handler.js', 'balance', '-m', mnemonics, '-i', '0'],
            capture_output=True, text=True, check=True, timeout=30)
    except subprocess.TimeoutExpired:
        response = subprocess.run(
            ['node', 'static/src/js/api_handler.js', 'balance', '-m', mnemonics, '-i', '0'],
            capture_output=True, text=True, check=True, timeout=30)

    return json.loads(response.stdout)


def address_balance(address, **kwargs):
    timeout = 20
    p = subprocess.run(
        ['node', 'static/src/js/api_handler.js', 'addressBalance', '-a', address],
        capture_output=True, text=True, check=True, timeout=timeout)
    return json.loads(p.stdout)


def update_(**kwargs):
    mnemonics = kwargs['mnemonics']
    print(mnemonics)
    try:
        response = subprocess.run(
            ['node', 'static/src/js/api_handler.js', 'update', '-m', mnemonics, '-i', '0'],
            capture_output=True, text=True, check=True, timeout=60)
    except subprocess.TimeoutExpired:
        response = subprocess.run(
            ['node', 'static/src/js/api_handler.js', 'update', '-m', mnemonics, '-i', '0'],
            capture_output=True, text=True, check=True, timeout=60)

    return json.loads(response.stdout)


def send(**kwargs):
    mnemonics = kwargs['mnemonics']
    timeout = 90
    address = kwargs['toAddress']
    amount = str(kwargs['amount'])
    token = kwargs['tokenId']
    try:
        p = subprocess.run(
            ['node', 'static/src/js/api_handler.js',
             'send', '-m', mnemonics, '-i', '0',
             '-d', address, '-t', token, '-a', amount
             ],
            capture_output=True, text=True, check=True, timeout=timeout)
    except subprocess.TimeoutExpired:

        p = subprocess.run(
            ['node', 'static/src/js/api_handler.js',
             'send', '-m', mnemonics, '-i', '0',
             '-d', address, '-t', token, '-a', amount
             ],
            capture_output=True, text=True, check=True, timeout=timeout)

    return json.loads(p.stdout)


def create():
    p = subprocess.run(
        ['node', 'static/src/js/api_handler.js', 'create'],
        capture_output=True, text=True, check=True)
    return json.loads(p.stdout)

