"""Joanie Payment application"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PaymentConfig(AppConfig):
    """Configuration class for the joanie payment app."""

    name = "joanie.payment"
    verbose_name = _("Joanie payment application")
