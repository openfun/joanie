"""Joanie Badges application"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BadgesConfig(AppConfig):
    """Configuration class for the joanie badges app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "joanie.badges"
    verbose_name = _("Joanie's badges application")
