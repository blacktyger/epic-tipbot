from django.contrib import admin
from .models import Subscription, TelegramUser, TelegramMessage, ViteAccountEvent, Token, ViteUnreceivedAccountEvent


admin.site.register((TelegramUser, Subscription, TelegramMessage, ViteAccountEvent, Token, ViteUnreceivedAccountEvent))