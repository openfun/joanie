"""
Base backend to pay online and save credit card
"""
import datetime
from calendar import monthrange

from django.conf import settings
from django.utils.module_loading import import_string


def get_backend(backend=None):
    """Allow to load payment backend from string dotted path"""
    backend_class = import_string(backend or settings.JOANIE_PAYMENT_BACKEND)
    return backend_class()


def compute_expiration_date(credit_card_expiration):
    """Compute expiration date from credit card data

    Args:
        credit_card_expiration: str, e.g. "01/23" ("%m/%y")

    Returns:
        datetime
    """
    month, year = credit_card_expiration.split("/")
    return datetime.date(
        int(year),
        int(month),
        monthrange(int(year), int(month))[1],  # last day
    )


class PaymentError(Exception):
    """Base class for payment error"""

    def __init__(self, messages):
        super().__init__()
        self.messages = messages


class PaymentNetworkError(PaymentError):
    """A network error has occurred while accessing payment service"""


class PaymentServiceError(PaymentError):
    """Payment service exceptions and faults"""


class PaymentBackend:
    """The backend has unique interface to request payments"""

    # pylint: disable=too-many-arguments
    def request_payment(
        self, card_number, cryptogram, expiration_date, price, reference
    ):
        """Send a payment request to pay with credit card data.
        Log info and error payment events.

        Args:
            card_number: str, credit card number
            cryptogram: str, credit card cryptogram
            expiration_date: str, credit card expiration (month/year)
            price: decimal, price to pay
            reference: uid, transaction reference

        Returns:
            True if payment success

        Raises:
            PaymentNetworkError or PaymentServiceError
        """
        raise NotImplementedError()

    def request_oneclick_payment(self, credit_card, price, reference):
        """Send a payment request to pay with credit card already registered.
        Log info and error payment events.

        Args:
            credit_card: instance of CreditCard
            price: decimal, price to pay
            reference: uid, transaction reference

        Returns:
            True if payment success

        Raises:
            PaymentNetworkError or PaymentServiceError
        """
        raise NotImplementedError()

    def register_credit_card(self, card_number, cryptogram, expiration_date):
        """Register a credit card to allow oneclick payment.
        Log info and error payment service events.

        Args:
            card_number: str, credit card number
            cryptogram: str, credit card cryptogram
            expiration_date: str, credit card expiration (month/year)

        Returns:
            uid, token:
                uid that should be used for credit card object creation,
                token that should be saved on credit card object and used for oneclick payment

        Raises:
            PaymentNetworkError or PaymentServiceError
        """
        raise NotImplementedError()

    def remove_credit_card(self, credit_card):
        """Remove credit card registration.
        Log info and error payment service events.

        Args:
            credit_card: instance of CreditCard

        Returns:
            uid: credit card uid removed

        Raises:
            PaymentNetworkError or PaymentServiceError
        """
        raise NotImplementedError()
