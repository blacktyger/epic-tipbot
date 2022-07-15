import threading
import time

from django.db.models import UniqueConstraint
from unixtimestampfield.fields import UnixTimeStampField
from django.contrib.auth.models import AbstractUser
from django.db import models

from datetime import datetime, timedelta
import uuid

from .managers import CustomUserManager


class TelegramUser(AbstractUser):
    id = models.BigIntegerField(unique=True, primary_key=True)
    is_bot = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    username = models.CharField(max_length=128, blank=True, null=True)
    last_name = models.CharField(max_length=128, blank=True, null=True)
    first_name = models.CharField(max_length=128, blank=True, null=True)
    language_code = models.CharField(max_length=16, blank=True, null=True)

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        constraints = [
            UniqueConstraint(fields=('id', 'username'), name='id_and_username'),
            UniqueConstraint(fields=('id', 'first_name'), name='id_and_first_name'),
            ]

    def temp_lock(self, time_: int = 2):
        self.locked = True
        self.save()

        thread = threading.Thread(target=self.unlock, args=[time_])
        thread.start()

    def unlock(self, time_: int):
        if self.locked:
            time.sleep(time_)
            self.locked = False
            self.save()

    @property
    def full_name(self):
        """
        You can get full name of user.

        :return: str
        """
        full_name = self.first_name
        if self.last_name:
            full_name += ' ' + self.last_name
        return full_name

    @property
    def name(self):
        if self.username:
            return self.username
        else:
            return self.full_name

    @property
    def mention(self):
        """
        You can get user's username to mention him
        Full name will be returned if user has no username

        :return: str
        """
        if self.username:
            return '@' + self.username
        return self.full_name

    def __str__(self):
        return f"{self.name}({self.id})"


class Token(models.Model):
    id = models.CharField(max_length=28, primary_key=True, unique=True)
    name = models.CharField(max_length=32)
    symbol = models.CharField(max_length=16)
    decimals = models.IntegerField()
    max_supply = models.CharField(max_length=1024)
    total_supply = models.CharField(max_length=1024)
    owner_address = models.CharField(max_length=55)

    objects = models.Manager()

    def __str__(self):
        return f"Token({self.symbol})"


# =========================================================================
PAYMENT_ADDRESS = "vite_3302b03807d55c2673fe8db1516e90d0df0d5b1fcb7dff0b68"
PAYMENT_VALUE = 1

class ViteAccountEvent(models.Model):
    height = models.IntegerField()
    amount = models.DecimalField(decimal_places=0, max_digits=60)
    details = models.JSONField()
    timestamp = UnixTimeStampField(default=0.0)
    block_type = models.CharField(max_length=32)
    account_address = models.CharField(max_length=55)

    token = models.ForeignKey(Token, null=True, blank=True, on_delete=models.CASCADE)
    objects = models.Manager()

    class Meta:
        unique_together = ('height', 'account_address')
        ordering = ['-timestamp']

    def __str__(self):
        return f"Event([{self.height}] {self.account_address} {self.token.symbol})"


class ViteUnreceivedAccountEvent(ViteAccountEvent):
    def __str__(self):
        return f"UnreceivedEvent([{self.height}] {self.account_address} {self.token.symbol})"


class TelegramMessage(models.Model):
    id = models.IntegerField(unique=True, primary_key=True)
    date = UnixTimeStampField(default=0.0)
    text = models.CharField(max_length=1024, default='')
    chat = models.JSONField()
    entities = models.JSONField()
    objects = models.Manager()

    user = models.ForeignKey(TelegramUser, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f"TelegramMessage(ID: {self.id} | USER: {self.user})"


class Subscription(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    vite_address = models.CharField(max_length=55)
    payment_address = models.CharField(max_length=55, default=PAYMENT_ADDRESS)
    payment_value = models.DecimalField(max_digits=32, decimal_places=8, default=PAYMENT_VALUE)
    period_days = models.IntegerField(default=7)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    # payment = models.OneToOneField('Transaction', blank=True, null=True, on_delete=models.SET_NULL)
    error = models.CharField(max_length=256, blank=True, null=True)
    objects = models.Manager()

    def _start_timer(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(days=7)
        self.save()

    def update_status(self):
        if self.is_active or self.is_paid:
            if datetime.now() <= self.end_time:
                pass
            else:
                self.is_active = self.is_paid = False
                print(f"{self.user} Subscription time is over, switching off!")
                self.save()

    def time_left(self) -> timedelta:
        now = datetime.now()
        delta = self.end_time - now
        print(delta)
        return delta

    def activate(self):
        if self.vite_address:
            self.is_active = True
            self.is_paid = True
            self._start_timer()
            self.save()
            print(f"Subscription for {self.vite_address} is activated")

    def __str__(self):
        return f"Subscription(USER: {self.user.id} | ADDRESS: {self.vite_address})"


""":arg
    'tokenInfo': {
      'tokenName': 'Epic Cash',
      'tokenSymbol': 'EPIC',
      'totalSupp ly': '890000000000000',
      'decimals': 8,
      'owner': 'vite_721a68f6ebd764e3f932832a05d87f8b1e8428393a0025bc72',
      'tokenId': 'tti_f370fadb275bc2a1a839c753',
      'maxSupply': '2100000 000000000',
      'ownerBurnOnly': True,
      'isReIssuable': True,
      'index': 2,
      'isOwnerBurnOnly': True

"""

"""
tg message dict:

{"message_id": 4848, 
  "from": {
    "id": 803516752, 
    "is_bot": false, 
    "first_name": "`blacktyger", 
    "last_name": "Freeman", 
    "username": "blacktyg3r", 
    "language_code": "en"}, 
    "chat": {
        "id": 803516752, 
        "first_name": "`blacktyger", 
        "last_name": "Freeman", 
        "username": "blacktyg3r", 
        "type": "private" }, 
    "date": 1637229414, 
    "text": "/start", 
    "entities": [{"type": "bot_command", "offset": 0, "length": 6}]
  }
};

"""
""":arg
accountAddress: "vite_15d3230e3c31c009c968beea7160ae98b491475236ae2cddbc"
address: "vite_15d3230e3c31c009c968beea7160ae98b491475236ae2cddbc"
amount: "100000000"
blockType: 2
confirmations: "5291"
confirmedHash: "b46b919b94a9954818bf1804eaa8384fdbca50c5cb2b915e8c5a2ae820e2465f"
confirmedTimes: "5291"
data: "MZ5G3Q=="
difficulty: null
fee: "0"
firstSnapshotHash: "b46b919b94a9954818bf1804eaa8384fdbca50c5cb2b915e8c5a2ae820e2465f"
firstSnapshotHeight: "78180485"
fromAddress: "vite_15d3230e3c31c009c968beea7160ae98b491475236ae2cddbc"
fromBlockHash: "0000000000000000000000000000000000000000000000000000000000000000"
hash: "b405ac3f46485864ac1302db21c84c6506c7c0d4c038612665f663c22ec6c11b"
height: "632"
logHash: null
nonce: null
prevHash: "3072b1e4f2115c352cd94c84f1d109c3b9df42a3a34c28585d76c8eb8515e885"
previousHash: "3072b1e4f2115c352cd94c84f1d109c3b9df42a3a34c28585d76c8eb8515e885"
producer: "vite_15d3230e3c31c009c968beea7160ae98b491475236ae2cddbc"
publicKey: "LgiZIygJ/JgXEixF851nz7CKFResl1QiLtq8bs7g+Qw="
quota: "21112"
quotaByStake: "21112"
quotaUsed: "21112"
receiveBlockHash: "272cc93a87a23cae325c2c0889235dab2a5db0df388323ae1ef5750b6ca9dd57"
receiveBlockHeight: "66328596"
sendBlockHash: "0000000000000000000000000000000000000000000000000000000000000000"
sendBlockList: null
signature: "0Ceo+kfY9GUzRJXdIw4SfwM2LLrwqaLNcvDvPYulmLLkQ/EWjLJtZJqj1f0XJjQ+dVqz4kDy1vksH+0a+FGuBQ=="
timestamp: 1638380245
toAddress: "vite_0000000000000000000000000000000000000006e82b8ba657"
tokenId: "tti_f370fadb275bc2a1a839c753"
tokenInfo:
decimals: 8
index: 2
isOwnerBurnOnly: true
isReIssuable: true
maxSupply: "2100000000000000"
owner: "vite_721a68f6ebd764e3f932832a05d87f8b1e8428393a0025bc72"
ownerBurnOnly: true
tokenId: "tti_f370fadb275bc2a1a839c753"
tokenName: "Epic Cash"
tokenSymbol: "EPIC"
totalSupply: "890000000000000"

"""