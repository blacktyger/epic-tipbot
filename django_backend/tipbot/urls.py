from django.urls import re_path
from .views import *


urlpatterns = [
    re_path('update/', update, name='update'),
    re_path('balance/', get_balance, name='get-balance'),
    re_path('address/', get_address, name='get-address'),
    re_path('create_alias/', AccountAliasCreateView.as_view(), name='create-alias'),
    re_path('get_mnemonics/', get_mnemonics, name='get-mnemonics'),
    re_path('send_transaction/', send_transaction, name='send-transaction'),

    ]
