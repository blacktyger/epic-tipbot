from rest_framework import serializers

from .models import Wallet, Transaction, AccountAlias


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('user', 'address', 'balance')


class ViteTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('sender', 'receiver', 'address', 'amount', 'token', 'status', 'message', 'data')

class EpicTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('sender', 'receiver', 'address', 'amount', 'status', 'message', 'coin', 'data')

class AccountAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountAlias
        fields = ('address', 'title', 'details', 'network', 'owner')


