"""Long Telegram strings"""
from ..fees import ViteFee


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
    if isinstance(args[2], str) and ('wrong' in args[2] or 'Create' in args[2]):
        epic_balance_1 = f"🟡 `{args[2]}`"
        epic_balance_2 = args[3]
    elif args[4]:
        epic_balance_1 = f"🪙  `{args[2]}`  *EPIC*"
        epic_balance_2 = f"💲  `{args[3]}`"
    else:
        epic_balance_1 = f"🪙  `{args[2]}`  *EPIC*"
        epic_balance_2 = f"💲  `{args[3]}`"

    return \
        f"""
{TITLE}
{LINE}
{VITE_T}
🪙  `{args[0]}`  *EPIC*
💲  `{args[1]}`                 
{LINE}
{EPIC_T}
{epic_balance_1}
{epic_balance_2}{args[4]}
{LINE}
"""


def epic_balance_details(balance):
    return \
f"""🔍 *EPIC Balance Details*
{LINE}
Available: `{balance.spendable}`
Pending: `{balance.pending}`
Locked: `{balance.locked}`

Outputs: `{balance.outputs}`
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


HELP_STRING = \
    """
🤖 *Hey, I'm Epic-Cash Tip-Bot* 👋

To signup with new account:
👉 /create

▪️ You will receive one-time link with your wallet *seed phrase* and *Tip-Bot* account *password* - please save them somewhere safe! 

▪️ Now you can deposit Epic-Cash to your wallet from *Vite Mobile/Desktop or Web app*, more details at vite.org.

▪️ Anyone with Tip-Bot account can tip or be tipped by @username:

👉 tip @blacktyg3r 0.1

▪️ to manage your *Wallet*:
👉 /wallet

Need help? [@blacktyg3r](https://t.me/blacktyg3r)    
"""

FAQ_STRING = \
    f"""
ℹ️ *Epic Tip-Bot FAQ*

👉 *What exactly is Tip-Bot Wallet?*
▪️ It is fully functional wallet on the VITE blockchain connected to your Telegram account.

👉 *Do I need Vite app to use Tip Bot?*
▪️ You can start using Tip-Bot right away and receive tips, but to deposit or withdraw you will need [Vite wallet](https://app.vite.net/).

👉 *How much does it cost?*
▪️ Using Epic Tip-Bot is *free*, transactions have fees, withdraw to other Vite wallets: *{ViteFee().fee_values()['withdraw']} EPIC* and Tip/Send: *{ViteFee().fee_values()['tip']}%*.

👉 *Is it safe?*
▪️ This is custodial solution, means software have access to your private keys. Although all security measures are in place, there is always risk of losing funds - *use only for low value operations and withdraw regularly!*

👉 *Can I send EPIC to someone without Tip-Bot account?*
▪️ You can also send/withdraw from your wallet to any valid VITE address (starting with `vite_...`).
"""
