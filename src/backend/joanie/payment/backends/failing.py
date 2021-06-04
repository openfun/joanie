"""Mock payment backend failure"""
import logging

from django.conf import settings

from . import base

logger = logging.getLogger(__name__)


class FailingBackend(base.PaymentBackend):
    """Backend to mock payment service failure"""

    # pylint: disable=too-many-arguments
    def request_payment(
        self, card_number, cryptogram, expiration_date, price, reference
    ):
        logger.error(
            "Payment %s with credit card %s failed with error: 'XXXX' for order %s",
            f"{price}{settings.JOANIE_CURRENCY[0]}",
            f"****{card_number[-4:]}",
            reference,
        )
        raise base.PaymentServiceError("[XXXX] Service failed")

    def request_oneclick_payment(self, credit_card, price, reference):
        logger.error(
            "Oneclick payment %s with credit card %s failed with error: 'XXXX'"
            " for order %s (credit card: %s)",
            f"{price}{settings.JOANIE_CURRENCY[0]}",
            f"****{credit_card.last_numbers}",
            reference,
            credit_card.uid,
        )
        raise base.PaymentServiceError("[XXXX] Service failed")

    def register_credit_card(self, card_number, cryptogram, expiration_date):
        logger.error(
            "Registration credit card %s failed with error: 'XXXX'",
            f"****{card_number[-4:]}",
        )
        raise base.PaymentServiceError("[XXXX] Service failed")

    def remove_credit_card(self, credit_card):
        logger.error(
            "Remove credit card %s failed with error: 'XXXX' (credit card: %s)",
            f"****{credit_card.last_numbers}",
            credit_card.uid,
        )
        raise base.PaymentServiceError("[XXXX] Service failed")
