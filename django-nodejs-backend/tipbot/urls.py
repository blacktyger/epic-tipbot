from django.conf.urls import url
from .views import *


urlpatterns = [
    url('address_balance/', get_address_balance, name='get-address-balance'),
    url('update/', update, name='update'),
    url('balance/', get_balance, name='get-balance'),
    url('address/', get_address, name='get-address'),
    url('create_alias', AccountAliasCreateView.as_view(), name='create-alias'),
    url('send_transaction/', send_transaction, name='send-transaction'),

    ]
