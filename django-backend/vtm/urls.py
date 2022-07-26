from django.conf.urls import url
from .views import CreateTelegramUserView

urlpatterns = [
    url('users/create', CreateTelegramUserView.as_view(), name='create-user'),

    ]