from django.urls import re_path
from .views import *


urlpatterns = [
    re_path('ports/', ports, name='ports'),
    re_path('update/', update, name='update'),
    re_path('balance/', get_balance, name='get-balance'),
    re_path('address/', get_address, name='get-address'),
    re_path('save_wallet/', save_wallet, name='save-wallet'),
    re_path('transactions/', TransactionView.as_view({'get': 'list'}), name='transactions'),
    re_path('create_alias/', AccountAliasCreateView.as_view(), name='create-alias'),
    re_path('get_mnemonics/', get_mnemonics, name='get-mnemonics'),
    re_path('send_transaction/', send_transaction, name='send-transaction'),
    re_path('save_transaction/', save_epic_transaction, name='save-epic-transaction'),
    re_path('update_transaction/', update_epic_transaction, name='update-epic-transaction'),

    ]
