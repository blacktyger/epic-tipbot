def loading_wallet_1():
    return \
f"""
*Epic-Cash TipBot Wallet*
====================
🔳 `Loading wallet..`

====================
"""


def loading_wallet_2():
    return \
f"""
*Epic-Cash TipBot Wallet*
====================
🔲 `Loading wallet..`

====================
"""


def connection_error_wallet():
    return \
f"""
*Epic-Cash TipBot Wallet*
====================
🟠 `Connection error`
      
====================
"""


def invalid_wallet():
    return \
        f"""
*Epic-Cash TipBot Wallet*
====================
ℹ️  `Create wallet first`
👉 /create
====================
"""


def ready_wallet(*args):
    return \
f"""
*Epic-Cash TipBot Wallet*
====================
🪙  *{args[0]}  EPIC*
💲  `{args[1]}`                 
====================
"""