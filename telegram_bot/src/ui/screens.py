"""Long Telegram strings"""

TITLE = "  🤖 *TIP-BOT WALLET*"
LINE = "➖➖➖➖➖➖➖➖"

VITE_T = "🔓 *VITE Blockchain*"
EPIC_T = "🔐 *EPIC Blockchain*"


def vite_loading_wallet_1():
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
◻️️ `Loading wallet..`

{LINE}
{EPIC_T}
◻️️ `Loading wallet..`

{LINE}
"""


def vite_loading_wallet_2():
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
▫️ `Loading wallet..`

{LINE}
{EPIC_T}
▫️ `Loading wallet..`

{LINE}
"""

def epic_loading_wallet_1(*args):
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🪙  `{args[0]}`  *EPIC*
💲  `{args[1]}` 
{LINE}
{EPIC_T}
◻️️ `Loading wallet..`

{LINE}
"""


def epic_loading_wallet_2(*args):
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🪙  `{args[0]}`  *EPIC*
💲  `{args[1]}` 
{LINE}
{EPIC_T}
▫️ `Loading wallet..`

{LINE}
"""

def vite_pending_1(*args):
    plural = 's' if int(args[0]) > 1 else ''
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🟢 `{args[0]} New transaction{plural}`
`Updating balance.`
{LINE}
{EPIC_T}
◻️️ `Loading wallet..`

{LINE}
"""


def vite_pending_2(*args):
    plural = 's' if int(args[0]) > 1 else ''
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
⚪️ `{args[0]} New transaction{plural}`
`Updating balance..`
{LINE}
{EPIC_T}
▫️ `Loading wallet..`

{LINE}
"""


def connection_error_wallet():
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🟠 `@EpicTipBot is offline`
❔  Temporary connection issue
{LINE}
{EPIC_T}
{LINE}
"""


def no_wallet():
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
ℹ️  `Create wallet first`
👉 /create
{LINE}
{EPIC_T}
{LINE}
"""


def invalid_wallet():
    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🟠️  `No wallet found`
❔  @EpicTipBotSupport
{LINE}
{EPIC_T}
{LINE}
"""


def ready_wallet(*args):
    if isinstance(args[2], str) and 'Error' in args[2]:
        epic_balance = f"🟡 `{args[2]}`"
    else:
        epic_balance = f"🪙  `{args[2]}`  *EPIC*"

    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🪙  `{args[0]}`  *EPIC*
💲  `{args[1]}`                 
{LINE}
{EPIC_T}
{epic_balance}
💲  `{args[3]}`
{LINE}
"""


def vite_mnemonics(link: str):
    return \
        f'''
▪️ To display your mnemonic seed phrase use the link below:

👉 <b><a href="{link}">WALLET SEED-PHRASE</a></b>

▪️ It is possible to view it only <b>once</b>!
'''


def new_vite_wallet_string(payload):
    payload_ = payload['data']
    return \
        f'''
<b>✅  Your Wallet is created!</b>

▪️Now please, visit the link below:
❗️<b><a href="{payload_}">WALLET SEED-PHRASE</a></b>
▪️and backup what's inside 👆


➡️ <b><a href='https://t.me/EpicTechGist/29'>Mobile Video Instructions</a></b>

➡️ <b><a href='https://blacktyg3r.com/funding'>Support Project</a></b>

➡️ Join <b>@EpicTipBotSupport</b>

▪️ Find out more 👉 /help /faq 

<b>Open your wallet 📲 /wallet</b>

'''

def update_v_2_5():
    return \
        f"""
☑️ <b>@EpicTipBot v2.5 Update List of Changes:</b>

▪️ Migration to new, much faster, production server
▪️ Adding transaction fees
▪️ Adding option to request the seed phrase
▪️ Minor fixes and improvements

This update will introduce transactions fees used to cover constantly growing running costs of the project:

👉 Deposits remain free
👉 Withdrawals to other Vite wallets (i.e. Vite App) are charged 0.5 EPIC each
👉 Tips are charged 1% of the transaction value

From now users can also request mnemonic seed phrase of the @TipBotWallet, in order to get the OneTimeSecret link please click/tap

👉 /get_mnemonics

Have questions? Join @EpicTipBotSupport group!
    """