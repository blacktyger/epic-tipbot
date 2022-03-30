from django.conf.urls import url
from .views import *

urlpatterns = [
    url('balance/', get_balance, name='get-balance'),
    url('address/', get_address, name='get-address'),
    url('send_transaction/', send_transaction, name='send-transaction'),

    ]