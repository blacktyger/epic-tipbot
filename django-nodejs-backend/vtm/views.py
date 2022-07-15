from django.views.generic import CreateView
from django.http import JsonResponse
from rest_framework import viewsets
from django.db.models import Q

from core.logger_ import setup_logging
from .serializers import *
from core import utils
from .models import *


logger = setup_logging(name=__name__, console_log_output="stdout", console_log_level="info", console_log_color=True,
                       logfile_file=__name__ + ".log", logfile_log_level="info", logfile_log_color=False,
                       log_line_template="%(color_on)s[%(asctime)s] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s")


class TelegramUserView(viewsets.ModelViewSet):
    """
    Use to query TelegramUser
    endpoint: 'users/'

    From where we expect requests:
    - ./src/user.py -> TipBotUser::_update_from_db()

    """
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        queryset = TelegramUser.objects.all()

        # List of possible params in request
        params_names = ['id', 'first_name', 'last_name', 'username', 'part_username']

        # Process received params from request and return queryset
        data = {param: self.request.query_params.get(param) for param in params_names}
        logger.info(f"[{data}]: get_users api call")

        if data['id']:
            return queryset.filter(id=data['id'])

        if data['username']:
            only_username_qs = queryset.filter(username__iexact=data['username'])
            logger.info(f"TelegramUserView::get_queryset(only_username_qs) - {only_username_qs}")

            if only_username_qs.count() > 1 and data['first_name']:
                username_and_first_qs = only_username_qs.filter(first_name__iexact=data['first_name'])
                logger.info(f"TelegramUserView::get_queryset(username_and_first_qs) - {username_and_first_qs}")
                return username_and_first_qs if username_and_first_qs else only_username_qs
            else:
                return only_username_qs

        if data['first_name']:
            only_first_name_qs = queryset.filter(first_name__iexact=data['first_name'])

            if only_first_name_qs.count() > 1:
                first_and_last_qs = queryset.filter(last_name__iexact=data['last_name'])
                return first_and_last_qs if first_and_last_qs else only_first_name_qs
            else:
                return only_first_name_qs

        # Use with caution, it is partial lookup, multiple records queryset most likely
        if data['part_username']:
            queryset = queryset.filter(Q(username__icontains=data['part_username']) |
                                       Q(first_name__icontains=data['part_username']))

        return queryset


class TokenView(viewsets.ModelViewSet):
    serializer_class = TokenSerializer

    def get_queryset(self):
        queryset = Token.objects.all()
        symbol = self.request.query_params.get('symbol')
        token_id = self.request.query_params.get('token_id')

        if token_id:
            queryset = queryset.filter(id=token_id)

        if symbol:
            queryset = queryset.filter(username=symbol)

        return queryset


class CreateTelegramUserView(CreateView):
    """
    Use to create new or update existing TelegramUser objects
    endpoint: 'users/create'

    From where we expect requests:
    - ./src/user.py -> TipBotUser::register()

    """
    model = TelegramUser

    def post(self, request, *args, **kwargs):
        user, exists = utils.get_or_create_telegram_user(request)
        serialized = TelegramUserSerializer(user)

        if exists:
            logger.info(f"[{user.mention}]: users/create (already exists)")
            response = {'error': 1, 'msg': 'account already active', 'data': serialized.data}
        else:
            vite_wallet = utils.create_vite_wallet(user)
            logger.info(f"[{user.mention}]: users/create (new)")

            if vite_wallet['error']:
                response = {'error': 1, 'msg': vite_wallet['msg'], 'data': None}
                logger.error(f"[{user.mention}]: create wallet: {vite_wallet['msg']}")
            else:
                secret_url = utils.create_wallet_secret(vite_wallet['data'], request)
                response = {'error': 0, 'msg': 'account registration success', 'data': secret_url}

        return JsonResponse(response)
