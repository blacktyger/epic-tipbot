from django.conf.urls import url
from .views import CreateSubscriptionView, AddViteAccountEventView, \
    ViteUnreceivedAccountEventView, CreateTelegramUserView

urlpatterns = [
    url('users/create', CreateTelegramUserView.as_view(), name='create_tg_acc'),
    # url('create_sub/', CreateSubscriptionView.as_view(), name='create_sub'),
    # url('add_account_event/', AddViteAccountEventView.as_view(), name='add_account_event'),
    # url('add_unreceived_account_event/', ViteUnreceivedAccountEventView.as_view(), name='add_unreceived_account_event'),

    ]