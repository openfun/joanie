"""Joanie Payment application"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PaymentConfig(AppConfig):
    """Configuration class for the joanie payment app."""

    name = "joanie.payment"
    verbose_name = _("Joanie payment application")

    # pylint: disable=import-outside-toplevel, unused-import
    def ready(self):
        """Import credit card post delete receiver."""
        from joanie.payment.models import (  # ,
            credit_card_post_delete_receiver,
        )
