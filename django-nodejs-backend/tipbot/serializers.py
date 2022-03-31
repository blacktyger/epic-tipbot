from rest_framework import serializers

from .models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('user', 'address', 'balance')


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('sender', 'receiver', 'address', 'amount', 'token', 'status', 'data')
