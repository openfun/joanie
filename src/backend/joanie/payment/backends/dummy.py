"""Mock payment backend dummy"""
import logging
import uuid

from django.conf import settings

from . import base

logger = logging.getLogger(__name__)


class DummyBackend(base.PaymentBackend):
    """Backend to mock payment service"""

    # pylint: disable=too-many-arguments
    def request_payment(
        self, card_number, cryptogram, expiration_date, price, reference
    ):
        logger.info(
            "Payment %s with credit card %s succeeded for order %s",
            f"{price}{settings.JOANIE_CURRENCY[0]}",
            f"****{card_number[-4:]}",
            reference,
        )
        return True

    def request_oneclick_payment(self, credit_card, price, reference):
        logger.info(
            "Oneclick payment %s with credit card %s succeeded"
            " for order %s (credit card: %s)",
            f"{price}{settings.JOANIE_CURRENCY[0]}",
            f"****{credit_card.last_numbers}",
            reference,
            credit_card.uid,
        )
        return True

    def register_credit_card(self, card_number, cryptogram, expiration_date):
        credit_card_uid = uuid.uuid4()
        token = "SLDLrcsLMPC"  # nosec
        logger.info(
            "Credit card %s successfully registered (credit card: %s)",
            f"****{card_number[-4:]}",
            credit_card_uid,
        )
        return credit_card_uid, token

    def remove_credit_card(self, credit_card):
        logger.info(
            "Remove credit card %s succeeded (credit card: %s)",
            f"****{credit_card.last_numbers}",
            credit_card.uid,
        )
        return credit_card.uid
