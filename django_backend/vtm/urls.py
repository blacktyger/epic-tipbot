from django.urls import re_path
from .views import CreateTelegramUserView

urlpatterns = [
    re_path('users/create', CreateTelegramUserView.as_view(), name='create_tg_acc'),

    ]