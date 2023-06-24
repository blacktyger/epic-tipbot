from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

from django_backend.secrets import encryption_key
from vtm.models import Token


class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    network = models.CharField(max_length=16, default='VITE')
    address = models.CharField(max_length=58, unique=True, primary_key=True)
    balance = models.JSONField(default=dict, null=True)
    mnemonics = models.TextField(max_length=2056, blank=True, null=True)

    objects = models.Manager()

    def decrypt_mnemonics(self):
        try:
            mnemonics_b = self.mnemonics.encode('utf-8')
            return Fernet(encryption_key).decrypt(mnemonics_b).decode('utf-8').lower()
        except Exception:
            return self.mnemonics

    def readable_balance(self):
        epic_id = 'tti_f370fadb275bc2a1a839c753'

        if self.balance and 'balanceInfoMap' in self.balance.keys() \
            and epic_id in self.balance['balanceInfoMap'].keys():

            epic = self.balance['balanceInfoMap'][epic_id]
            as_int = int(epic['balance'])
            decimals = epic['tokenInfo']['decimals']
            return round((as_int / 10**decimals), 8)
        else:
            return 0.0

    def __str__(self):
        return f"Wallet({self.user.mention} | {self.network} | {self.readable_balance()} EPIC)"


class AccountAlias(models.Model):
    """Represents alias for vite account"""
    tag = models.CharField(max_length=1, default='#')
    title = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey('vtm.TelegramUser', null=True, on_delete=models.SET_NULL, related_name='owner')
    address = models.CharField(max_length=58)
    network = models.CharField(max_length=16, default='VITE')
    details = models.JSONField(default=dict, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.title}({self.address[0:8]}...{self.address[-4:]})"

class Transaction(models.Model):
    network = models.CharField(max_length=16, default='VITE')
    token = models.ForeignKey(Token, blank=True, null=True, on_delete=models.SET_NULL, related_name='token')
    sender = models.ForeignKey(Wallet, null=True, on_delete=models.SET_NULL, related_name='sender_wallet')
    receiver = models.ForeignKey(Wallet, blank=True, null=True, on_delete=models.SET_NULL, related_name='receiver_wallet')
    address = models.CharField(max_length=58, null=True, blank=True)
    amount = models.DecimalField(decimal_places=8, max_digits=32, null=True)
    type_of = models.CharField(max_length=16, null=True, blank=True)
    status = models.CharField(max_length=10, default='pending')
    data = models.JSONField(default=dict)
    message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ('-timestamp', )

    def logs_repr(self):
        return f"Transaction({self.network} | {self.amount} {self.token.symbol} | " \
               f"{self.sender.user.mention if self.sender else ''} to --> " \
               f"{self.receiver.user.mention if self.receiver else self.address} |" \
               f" {self.type_of} | {self.status})"

    def __str__(self):
        return self.logs_repr()

    def prepare_amount(self):
        dec = 10 ** self.token.decimals if self.token else 8
        return int(self.amount * dec)

    def prepare_address(self):
        assert self.address or self.receiver
        if self.receiver:
            return self.receiver.address
        elif self.address:
            return self.address
