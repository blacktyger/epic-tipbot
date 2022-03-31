from django.views.generic import CreateView
from django.http import JsonResponse
from rest_framework import viewsets

from .serializers import *
from core import utils
from .models import *


class TelegramUserView(viewsets.ModelViewSet):
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        queryset = TelegramUser.objects.all()
        user_id = self.request.query_params.get('id')
        username = self.request.query_params.get('username')

        if user_id:
            queryset = queryset.filter(id=user_id)

        if username:
            queryset = queryset.filter(username=username)

        return queryset


class CreateTelegramUserView(CreateView):
    """
    Use to create new or update existing TelegramUser objects
    endpoint: 'users/create'
    """
    model = TelegramUser

    def post(self, request, *args, **kwargs):
        user, exists = utils.get_or_create_telegram_user(request)
        serialized = TelegramUserSerializer(user)

        if exists:
            response = {'error': 1, 'msg': 'Account already active.', 'data': serialized.data}
        else:
            wallet = utils.create_wallet(user)
            if wallet['error']:
                response = {'error': 1, 'msg': wallet['msg'], 'data': None}
            else:
                secret_url = utils.create_wallet_secret(wallet['data'], request)
                response = {'error': 0, 'msg': 'Account created successfully!', 'data': secret_url}

        return JsonResponse(response)


# ==========================================================================
#
# class SubscriptionView(viewsets.ModelViewSet):
#     serializer_class = SubscriptionSerializer
#
#     def get_queryset(self):
#         queryset = Subscription.objects.all()
#         is_active = self.request.query_params.get('is_active')
#         print(is_active)
#         if is_active:
#             queryset = queryset.filter(is_active=True)
#         return queryset
#
#
# class TelegramMessageView(viewsets.ModelViewSet):
#     serializer_class = TelegramMessageSerializer
#     queryset = TelegramMessage.objects.all()
#
#
# class ViteAccountEventView(viewsets.ModelViewSet):
#     serializer_class = ViteAccountEventSerializer
#
#     def get_queryset(self):
#         queryset = ViteAccountEvent.objects.all()
#         address = self.request.query_params.get('address')
#         last = self.request.query_params.get('last')
#         print(address, last)
#         if address:
#             queryset = queryset.filter(account_address=address)
#         if last:
#             queryset = [queryset.first()] if queryset.last() else []
#         return queryset


# def send_telegram_message(user: TelegramUser or None, message: str) -> None:
#     if user:
#         url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
#         params = {
#             'chat_id': user.id,
#             'text': message,
#             'parse_mode': 'markdown',
#             'disable_web': True,
#             'disable_web_page_preview': True,
#             }
#         print(f'sending message to @{user.username}')
#         requests.get(url, params=params)


# def get_vite_address_event_user(event: ViteAccountEvent) -> TelegramUser or None:
#     sub = Subscription.objects.filter(vite_address=event.account_address)
#     if sub:
#         return sub[0].user
#     return None


class AddViteAccountEventView(CreateView):
    """
    Save new Account Events (accountBlock on vite api) to database
    endpoint: 'add_account_event/'
    """
    # model = ViteAccountEvent
    #
    # def post(self, request, *args, **kwargs):
    #     new_events = []
    #     events = json.loads(request.body)
    #     # print(events)
    #
    #     # Handle new events from Vite blockchain
    #     for event in events:
    #         event, created = create_vite_account_event(event)
    #         if created:
    #             print('NEW: ', event)
    #             new_events.append(event)
    #
    #     # Handle single and multiple new events notification
    #     if new_events:
    #         if len(new_events) <= 2:
    #             messages = []
    #
    #             for i, event in enumerate(new_events):
    #                 messages.append(f'New activity: {new_events[i].token.symbol}')
    #
    #             message = '\n'.join(messages)
    #         else:
    #             message = f'{len(new_events)} New activities!'
    #
    #         # Send prepared message to user telegram
    #         user = get_vite_address_event_user(new_events[0])
    #         if user:
    #             send_telegram_message(user, message)
    #
    #     return JsonResponse({})


class ViteUnreceivedAccountEventView(AddViteAccountEventView):
    pass


# def create_vite_account_event(payload: dict) -> tuple:
#     if isinstance(payload, str):
#         print(payload)
#     else:
#         token = get_or_create_vite_token(payload['tokenInfo'])
#
#         event_data = {
#             'token': token,
#             'height': payload['height'],
#             'amount': payload['amount'],
#             'details': payload,
#             'block_type': payload['blockType'],
#             'timestamp': payload['timestamp'],
#             'account_address': payload['accountAddress']
#             }
#
#         event, created = ViteAccountEvent.objects.get_or_create(
#             height=int(payload['height']),
#             account_address=payload['accountAddress'],
#             defaults=event_data)
#
#         return event, created


class CreateSubscriptionView(CreateView):
    """
    Use to create new or update existing Subscription objects
    endpoint: 'create_sub/'
    """
    # model = Subscription
    #
    # def post(self, request, *args, **kwargs):
    #     response = {'error': 1, 'msg': 'unknown error', 'data': None}
    #
    #     # try:
    #     message_data = json.loads(request.body)
    #     message = TelegramMessage.objects.create(**message_data)
    #     address = message.text.split(' ')[1]
    #     user = get_or_create_telegram_user(message_data)
    #
    #     if is_valid_vite_address(address):
    #         active_subs = [s for s in Subscription.objects.filter(
    #             user=user, vite_address=address) if s.is_active]
    #         if active_subs:
    #             serialized = SubscriptionSerializer(active_subs[0])
    #             response = {'error': 0, 'msg': 'sub_already_active', 'data': serialized.data}
    #         else:
    #             sub, created = Subscription.objects.get_or_create(user=user, vite_address=address)
    #             serialized = SubscriptionSerializer(sub)
    #             response = {'error': 0, 'msg': 'sub_created', 'data': serialized.data}
    #
    #     # except Exception as e:
    #     #     response = {'error': 1, 'msg': str(e), 'data': None}
    #
    #     return JsonResponse(response)