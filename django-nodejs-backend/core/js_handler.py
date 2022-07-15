import concurrent.futures
import subprocess
import json


def balance(**kwargs):
    mnemonics = kwargs['mnemonics']
    timeout = kwargs['timeout'] if 'timeout' in kwargs.keys() else 2
    p = subprocess.run(
        ['node', 'static/src/js/api_handler.js', 'balance', '-m', mnemonics, '-i', '0'],
        capture_output=True, text=True, check=True, timeout=timeout)
    return json.loads(p.stdout)


def update_(**kwargs):
    mnemonics = kwargs['mnemonics']
    timeout = kwargs['timeout'] if 'timeout' in kwargs.keys() else 15

    p = subprocess.run(
        ['node', 'static/src/js/api_handler.js', 'update', '-m', mnemonics, '-i', '0'],
        capture_output=True, text=True, check=True, timeout=timeout)
    return json.loads(p.stdout)


def send(**kwargs):
    mnemonics = kwargs['mnemonics']
    timeout = kwargs['timeout'] if 'timeout' in kwargs.keys() else 10
    address = kwargs['toAddress']
    amount = str(kwargs['amount'])
    token = kwargs['tokenId']

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


def execute_node_call(**kwargs):
    """
    Helper function to "spam" the node script until we get a response.
    We make n number of tries, each failed attempt will make timeout 0.5sec longer
    until we get a response. Successful attempt will return response and break a loop.
    This is a dirty solution but works well :)
    """
    tries = kwargs['tries'] if 'tries' in kwargs.keys() else 5

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for i in range(tries):
            if i > 0:
                kwargs['timeout'] += i / 2

            a = executor.submit(eval(kwargs['func']), **kwargs)

            try:
                return a.result()
            except subprocess.TimeoutExpired:
                continue
