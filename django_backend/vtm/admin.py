from django.contrib import admin
from .models import *


admin.site.register((TelegramUser, Subscription, TelegramMessage, ViteAccountEvent, Token, ViteUnreceivedAccountEvent))