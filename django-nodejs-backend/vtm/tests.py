import json
import subprocess
import concurrent.futures
import time

import requests


mnemonics = "shop shield blush kiss blade peasant card object similar music agent surprise"


def balance(**kwargs):
    print(kwargs)
    mnemonics = kwargs['mnemonics']
    timeout = kwargs['timeout'] if kwargs['timeout'] else 2

    p = subprocess.run(
        ['node', 'D:/Users/IOPDG/Documents/telegram-vite-tipbot/django-nodejs-backend/static/src/js/api_handler.js',
         'balance', '-m', mnemonics, '-i', '0'],
        capture_output=True, text=True, check=True, timeout=timeout)
    return json.loads(p.stdout)


def update(**kwargs):
    print(kwargs)
    mnemonics = kwargs['mnemonics']
    timeout = kwargs['timeout'] if kwargs['timeout'] else 2

    p = subprocess.run(
        ['node', 'D:/Users/IOPDG/Documents/telegram-vite-tipbot/django-nodejs-backend/static/src/js/api_handler.js',
         'update', '-m', mnemonics, '-i', '0'],
        capture_output=True, text=True, check=True, timeout=timeout)
    return json.loads(p.stdout)


def execute_node_call(**kwargs):
    """
    Helper function to "spam" the node script until we get a response.
    We make n number of tries, each failed attempt will make timeout 0.5sec longer
    until we get a response. Successful attempt will return response and break a loop.
    This is a dirty solution but working well :)
    """
    tries = kwargs['tries'] if 'tries' in kwargs.keys() else 5

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for i in range(tries):
            if i > 0:
                kwargs['timeout'] += i/2

            a = executor.submit(eval(kwargs['func']), **kwargs)

            try:
                return a.result()
            except subprocess.TimeoutExpired:
                continue


print(execute_node_call(func='update', mnemonics=mnemonics, timeout=5))

