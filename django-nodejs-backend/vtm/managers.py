from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import ugettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where ID is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, id, password, **extra_fields):
        """
        Create and save a User with the given ID and username.
        """
        if not id:
            raise ValueError(_('Need Telegram ID'))

        user = self.model(id=id, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(**extra_fields)