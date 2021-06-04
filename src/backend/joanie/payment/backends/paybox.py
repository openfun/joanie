"""
Paybox payment backend
"""
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.http.request import QueryDict
from django.utils import timezone

import requests

from . import base

logger = logging.getLogger(__name__)


BANK_URL = settings.PAYBOX_BANK_URL
CODE_RESPONSE_OK = "00000"


def format_price(price):
    """Format price for Paybox.
    For example the price 15€00, value given can be an int, float, decimal or string,
    return 1500
    """
    return "{:.2f}".format(Decimal(price)).replace(".", "")


def format_expiration_date(date):
    """Format expiration date for Paybox.

    Args:
        date: str, month/year e.g. 01/23
    """
    return date.replace("/", "")


class Paybox(base.PaymentBackend):
    """Paybox payment service backend"""

    def __init__(self):
        self.bank_data = {
            # paybox account and subscription
            "SITE": settings.PAYBOX_SITE,  # site number from verifone
            "RANG": settings.PAYBOX_RANGE,  # range from merchant's bank
            "CLE": settings.PAYBOX_KEY,  # backoffice password
            # protocol PPPS version depends of paybox subscription
            "VERSION": "00104",  # paybox direct plus
            # 'ACTIVITE' is the kind of cashflow, value 020 is for no specified cashflow
            # allows us to not ask cryptogram to pay with credit card already registered
            # (unlike internet cashflow '024')
            "ACTIVITE": "020",
            "DEVISE": settings.JOANIE_CURRENCY[2],
            # sending timestamp
            "DATEQ": timezone.now().strftime("%d%m%Y"),
            # transaction data
            "TYPE": "",  # transaction kind (capture, debit...)
            "NUMQUESTION": "",  # id of request, unique for each request per day
            # credit card data
            "PORTEUR": "",  # credit card number or token if registered credit card
            "CVV": "",  # cryptogram (not required if credit card saved)
            "DATEVAL": "",  # credit card expiration date
            "REFABONNE": "",  # credit card uid (unique)
            # payment data
            "REFERENCE": "",  # optional, payment reference
            "MONTANT": "",  # price, 19€90 -> 1990
        }

    @staticmethod
    def _call_service(data):
        try:
            return requests.post(BANK_URL, data=data, timeout=30)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects,
        ) as err:
            logger.warning(err)
            raise base.PaymentNetworkError(f"Paybox service doesn't respond {err}")

    @staticmethod
    def _generate_request_id():
        """Paybox needs a unique id for each request per day
        This id has to be in range [1, 2147483647], so we generate an id depending on time.
        """
        return timezone.now().strftime("0%H%M%S%f")[:-3]

    @staticmethod
    def _check_consistency_response(bank_data, response_data):
        """SITE, RANG and NUMQUESTION sent are returned by the service faithfully
        According to Paybox those values returned has to be checked

        Args:
            bank_data: dict, bank data sent to service
            response_data: dict, response data returned by service

        Returns:
            list of unmatched data
        """
        return [
            key
            for key in ("SITE", "RANG", "NUMQUESTION")
            if bank_data[key] != response_data[key]
        ]

    @staticmethod
    def _extract_response_data(response):
        return QueryDict(response.content).dict()

    # pylint: disable=too-many-arguments
    def request_payment(
        self, card_number, cryptogram, expiration_date, price, reference
    ):
        """Pay with credit card data

        Args:
            card_number: str, e.g. 1111222233334444,
            cryptogram: str, e.g. 222,
            expiration_date: str, e.g. '09/21',
            price: decimal
            reference: uid, unique reference payment
        """
        data = self.bank_data.copy()

        # debit
        data["TYPE"] = "00003"

        # payment data
        data["MONTANT"] = format_price(price)
        data["REFERENCE"] = reference
        data["NUMQUESTION"] = self._generate_request_id()

        # credit card data
        data["PORTEUR"] = card_number
        data["CVV"] = cryptogram
        data["DATEVAL"] = format_expiration_date(expiration_date)

        price = f"{price}{settings.JOANIE_CURRENCY[0]}"

        response = self._call_service(data)
        if response.status_code != 200:
            error_status = f"[{response.status_code}] {response.content}"
        else:
            response_data = self._extract_response_data(response)
            consistency_failure = self._check_consistency_response(data, response_data)
            if response_data["CODEREPONSE"] != CODE_RESPONSE_OK:
                error_status = (
                    f"[{response_data['CODEREPONSE']}] {response_data['COMMENTAIRE']}"
                )
            elif consistency_failure:
                error_status = (
                    "Consistency check failure with data returned "
                    f"by service for {consistency_failure}"
                )
            else:
                logger.info(
                    "Payment %s with credit card %s succeeded for order %s",
                    price,
                    f"****{card_number[-4:]}",
                    reference,
                )
                return True
        logger.error(
            "Payment %s with credit card %s failed with error: '%s' for order %s",
            price,
            f"****{card_number[-4:]}",
            error_status,
            reference,
        )
        raise base.PaymentServiceError(error_status)

    def request_oneclick_payment(self, credit_card, price, reference):
        """Pay with already registered credit card

        Args:
            credit_card: CreditCard object,
            price: decimal,
            reference: uid,
        """
        data = self.bank_data.copy()
        data["TYPE"] = "00053"

        # payment data
        data["MONTANT"] = format_price(price)
        data["REFERENCE"] = reference
        data["NUMQUESTION"] = self._generate_request_id()

        # card data
        data["PORTEUR"] = credit_card.token
        data["REFABONNE"] = credit_card.uid
        data["DATEVAL"] = credit_card.expiration_date.strftime("%m%y")

        price = f"{price}{settings.JOANIE_CURRENCY[0]}"

        response = self._call_service(data)
        if response.status_code != 200:
            error_status = f"[{response.status_code}] {response.content}"
        else:
            response_data = self._extract_response_data(response)
            consistency_failure = self._check_consistency_response(data, response_data)
            if response_data["CODEREPONSE"] != CODE_RESPONSE_OK:
                error_status = (
                    f"[{response_data['CODEREPONSE']}] {response_data['COMMENTAIRE']}"
                )
            elif consistency_failure:
                error_status = (
                    "Consistency check failure with data returned "
                    f"by service for {consistency_failure}"
                )
            else:
                logger.info(
                    "Oneclick payment %s with credit card %s succeeded"
                    " for order %s (credit card: %s)",
                    price,
                    f"****{credit_card.last_numbers}",
                    reference,
                    credit_card.uid,
                )
                return True
        logger.error(
            "Oneclick payment %s with credit card %s failed with error: '%s'"
            " for order %s (credit card: %s)",
            price,
            f"****{credit_card.last_numbers}",
            error_status,
            reference,
            credit_card.uid,
        )
        raise base.PaymentServiceError(error_status)

    def register_credit_card(self, card_number, cryptogram, expiration_date):
        """Register credit card.

        Args:
            card_number: int, size 16
            cryptogram: int, size 3
            expiration_date: str, "month/year"

        Returns:
             credit card uid and token to use to pay
        """
        data = self.bank_data.copy()
        data["TYPE"] = "00056"
        data["NUMQUESTION"] = self._generate_request_id()
        data["MONTANT"] = "1"  # a minimal value is needed

        # credit card data
        data["PORTEUR"] = card_number
        data["CVV"] = cryptogram
        data["DATEVAL"] = format_expiration_date(expiration_date)

        # we define here a uid to share a reference with payment solution for the credit card
        credit_card_uid = uuid.uuid4()
        data["REFABONNE"] = credit_card_uid

        response = self._call_service(data)
        if response.status_code != 200:
            error_status = f"[{response.status_code}] {response.content}"
        else:
            response_data = self._extract_response_data(response)
            consistency_failure = self._check_consistency_response(data, response_data)
            if response_data["CODEREPONSE"] != CODE_RESPONSE_OK:
                error_status = (
                    f"[{response_data['CODEREPONSE']}] {response_data['COMMENTAIRE']}"
                )
            elif consistency_failure:
                error_status = (
                    "Consistency check failure with data returned "
                    f"by service for {consistency_failure}"
                )
            else:
                logger.info(
                    "Credit card %s successfully registered (credit card: %s)",
                    f"****{card_number[-4:]}",
                    credit_card_uid,
                )
                return credit_card_uid, response_data["PORTEUR"]  # token
        logger.error(
            "Registration credit card %s failed with error: '%s'",
            f"****{card_number[-4:]}",
            error_status,
        )
        raise base.PaymentServiceError(error_status)

    def remove_credit_card(self, credit_card):
        """Remove credit card on payment service side.

        Args:
            credit_card: CreditCard object,
        """
        data = self.bank_data.copy()
        data["TYPE"] = "00058"
        data["NUMQUESTION"] = self._generate_request_id()
        data["REFABONNE"] = credit_card.uid
        data["PORTEUR"] = credit_card.token
        data["DATEVAL"] = credit_card.expiration_date.strftime("%m%y")

        response = self._call_service(data)
        if response.status_code != 200:
            error_status = f"[{response.status_code}] {response.content}"
        else:
            response_data = self._extract_response_data(response)
            consistency_failure = self._check_consistency_response(data, response_data)
            if response_data["CODEREPONSE"] != CODE_RESPONSE_OK:
                error_status = (
                    f"[{response_data['CODEREPONSE']}] {response_data['COMMENTAIRE']}"
                )
            elif consistency_failure:
                error_status = (
                    "Consistency check failure with data returned "
                    f"by service for {consistency_failure}"
                )
            else:
                logger.info(
                    "Remove credit card %s succeeded (credit card: %s)",
                    f"****{credit_card.last_numbers}",
                    credit_card.uid,
                )
                return credit_card.uid
        logger.error(
            "Remove credit card %s failed with error: '%s' (credit card: %s)",
            f"****{credit_card.last_numbers}",
            error_status,
            credit_card.uid,
        )
        raise base.PaymentServiceError(error_status)
