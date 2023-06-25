from django.urls import path, include
from rest_framework import routers
from django.contrib import admin

from tipbot.views import TransactionView, WalletView, AccountAliasView
from vtm.views import TelegramUserView, TokenView
from tipbot import urls as tipbot_urls
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
    path('tipbot/', include(tipbot_urls)),
    path('admin/', admin.site.urls),
    path('api/', include(vtm_urls)),
    path('api/', include(router.urls)),
    ]
