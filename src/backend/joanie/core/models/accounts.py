"""
Declare and configure the models for the customers part
"""
import django.contrib.auth.models as auth_models
from django.utils.translation import gettext_lazy as _


class User(auth_models.AbstractUser):
    """User model which follow courses or manage backend (is_staff)"""

    class Meta:
        db_table = "joanie_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.username
