"""TEST UNIT FOR TELEGRAM EPIC-TIP-BOT"""
import random

from src import tools, user


def test_create_user():
    for i in range(10):
        print(f'--> Processing {i}')
        user.TipBotUser.create_test_user().register()

    # receiver = user.TipBotUser.create_test_user()
    # print(receiver.wallet)

    # assert sender and receiver
    # params = {'id': '6181380742', 'is_bot': True, 'username': None,
    #           'last_name': 'Levine', 'first_name': 'Macario', 'language_code': 'es'}
    # # sender1 = user.TipBotUser(id=67064141)
    # # sender2 = user.TipBotUser.create_test_user()
    # sender2 = user.TipBotUser(**params)
    # sender2.register()
    # sender3 = user.TipBotUser(username='peppermint')
    # sender4 = user.TipBotUser(username='peppermint')
    # sender5 = user.TipBotUser(first_name='Cipriano')
    # sender6 = user.TipBotUser.from_obj(sender)
    #
    # print(sender2.wallet)

    # user.TipBotUser.get_user(key_word='kasia')


# test_create_user()

# def test_send_tip():
#     sender = user.TipBotUser(username='blacktyg3r')
#     receiver = user.TipBotUser(username='epic_vitex_bot')
#     amount = 0.001
#
#     params = dict(sender=sender, receivers=[receiver, sender, receiver], amount=amount,
#                   network='VITE', type_of='tip')
#
#     sender.wallet.send_tip(params)
#

# test_send_tip()

# TODO: History Handle
# # /------ DISPLAY TX HISTORY HANDLE ------\ #
# @dp.message_handler(commands=COMMANDS['history'])
# async def history(message: types.Message):
#     user_query = 'users'
#     tx_query = 'transactions'
#     private_chat = message.from_user.id
#     user, message_ = tools.parse_user_and_message(message)
#
#     # Get UserTelegram Wallet instance to get transaction history
#     user = requests.get(url=f'{DJANGO_API_URL}/{user_query}/', params={'user_id': user['id']}).json()
#     user_wallet_address = user[0]['wallet'][0]
#
#     # Get transactions for that Wallet
#     transactions = requests.get(url=f'{DJANGO_API_URL}/{tx_query}/', params={'address': user_wallet_address})
#     transactions = json.loads(transactions.content)
#
#     # Sort transactions
#     received = [tx for tx in transactions if user_wallet_address in tx['address']]
#     send = [tx for tx in transactions if user_wallet_address in tx['sender']]
#
#     if not response['error']:
#         msg = f"📄  *Transactions History:*\n" \
#               f"`{response['data']}`\n"
#     else:
#         msg = f"🔴 {response['msg']}"