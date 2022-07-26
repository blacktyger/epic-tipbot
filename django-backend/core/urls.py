from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from tipbot.views import TransactionView, WalletView, AccountAliasCreateView, AccountAliasView
from tipbot import urls as tipbot_urls
from vtm.views import TelegramUserView, TokenView
from vtm import urls as vtm_urls
from .views import index


router = routers.DefaultRouter()
router.register(r'transactions', TransactionView, 'transactions')
router.register(r'wallets', WalletView, 'wallets')
router.register(r'tokens', TokenView, 'tokens')
router.register(r'users', TelegramUserView, 'users')
router.register(r'alias', AccountAliasView, 'alias')


urlpatterns = [
    path('', index),
    path('admin/', admin.site.urls),
    path('api/', include(vtm_urls)),
    path('api/', include(tipbot_urls)),
    path('api/', include(router.urls)),
    ]
