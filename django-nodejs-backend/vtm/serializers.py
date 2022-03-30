from rest_framework import serializers
from .models import Subscription, TelegramUser, TelegramMessage, ViteAccountEvent, ViteUnreceivedAccountEvent


class ViteAccountEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViteAccountEvent
        fields = ('__all__')


class ViteUnreceivedAccountEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViteUnreceivedAccountEvent
        fields = ('__all__')


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = ('id', 'username', 'first_name', 'language_code')


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('__all__')


class TelegramMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramMessage
        fields = ('__all__')


