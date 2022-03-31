from django.conf import settings
from django.db import models

from vtm.models import Token


class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    address = models.CharField(max_length=58, unique=True, primary_key=True)
    balance = models.JSONField(default=dict)
    mnemonics = models.TextField(max_length=512, blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.user.username}"


class Transaction(models.Model):
    token = models.ForeignKey(Token, blank=True, null=True, on_delete=models.CASCADE, related_name='token')
    sender = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='sender_wallet')
    receiver = models.ForeignKey(Wallet, blank=True, null=True, on_delete=models.CASCADE, related_name='receiver_wallet')

    address = models.CharField(max_length=58, null=True, blank=True)
    amount = models.DecimalField(decimal_places=8, max_digits=32, null=True)
    status = models.CharField(max_length=10, default='pending')
    data = models.JSONField(default=dict)
    message = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ('-timestamp', )

    def __str__(self):
        return f"Transaction({self.sender.user.username} -> {self.amount} -> " \
               f"{self.receiver.user.username if self.receiver else self.address})"

    def prepare_amount(self):
        dec = 10 ** self.token.decimals if self.token else 8
        return int(self.amount * dec)

    def prepare_address(self):
        assert self.address or self.receiver
        if self.receiver:
            return self.receiver.address
        elif self.address:
            return self.address

