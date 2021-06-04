"""Paybox payment backend test suite"""
import datetime
import decimal
import logging
import uuid
from calendar import monthrange
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

import requests

from joanie.core import factories
from joanie.payment import backends
from joanie.payment.backends.paybox import Paybox

PAYBOX_SITE = "1999888"
PAYBOX_RANGE = "32"
PAYBOX_KEY = "1999888I"
CREDIT_CARD_DATA = {
    "name": "Personal",
    "card_number": "1111222233334444",
    "expiration_date": (timezone.now() + datetime.timedelta(days=400)).strftime(
        "%m/%y"
    ),
    "cryptogram": "222",
}
NUMQUESTION = "0002322510"
PAYMENT_TOKEN = "SLDLrcsLMPC"  # nosec


def make_mock_response(status_code=200, content=""):
    """Make a basic mock requests.Response

    Args:
        status_code: int, status code e.g. 200, 400
        content: str, data response

    Returns:
        response: requests.Response object
    """
    response = requests.Response()
    response.status_code = status_code
    response._content = content  # pylint: disable=protected-access
    response.headers = requests.structures.CaseInsensitiveDict(
        {
            "Date": timezone.now().strftime("%a, %d %b %Y %T %Z"),
            "Server": "Apache",
            "Content-Length": len(content),
            "Keep-Alive": "timeout=15, max=100",
            "Connection": "Keep-Alive",
            "Content-Type": "text/html;charset=ISO-8859-1",
        }
    )
    return response


@override_settings(
    JOANIE_PAYMENT_BACKEND="joanie.payment.backends.paybox.Paybox",
    PAYBOX_BANK_URL="https://preprod-ppps.paybox.com/PPPS.php",
    PAYBOX_SITE=PAYBOX_SITE,
    PAYBOX_RANGE=PAYBOX_RANGE,
    PAYBOX_KEY=PAYBOX_KEY,
)
class PayboxTest(TestCase):
    """Paybox payment backend tests"""

    @patch.object(Paybox, "_call_service")
    @patch.object(Paybox, "_generate_request_id")
    def test_request_payment(self, mock_generate_request_id, mock_call_service):
        """Test payment with credit card data"""

        # mock numquestion generate to be sure to match with mocked service response
        mock_generate_request_id.return_value = NUMQUESTION

        # mock service response
        expected_content = (
            "NUMTRANS=0034813511&NUMAPPEL=0061544595&"
            f"NUMQUESTION={NUMQUESTION}&SITE={PAYBOX_SITE}&RANG={PAYBOX_RANGE}&"
            "AUTORISATION=XXXXXX&"
            "CODEREPONSE=00000&COMMENTAIRE=Demande trait\xe9e avec succ\xe8s&"
            "REFABONNE=&PORTEUR="
        )
        mock_call_service.return_value = make_mock_response(200, expected_content)

        # now call service to pay
        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            payment_backend = backends.get_backend()
            paid = payment_backend.request_payment(
                CREDIT_CARD_DATA["card_number"],
                CREDIT_CARD_DATA["cryptogram"],
                CREDIT_CARD_DATA["expiration_date"],
                decimal.Decimal(19.90),
                uuid.uuid4(),
            )
            self.assertTrue("succeeded" in logs.output[0])
            self.assertTrue(paid)

    @patch.object(Paybox, "_call_service")
    @patch.object(Paybox, "_generate_request_id")
    def test_register_credit_card(self, mock_generate_request_id, mock_call_service):
        """Test credit card registration"""

        # mock uid generate that will be used to create credit card
        future_credit_card_uid = uuid.uuid4()
        with patch("uuid.uuid4") as uuid4:
            uuid4.return_value = future_credit_card_uid

            # mock numquestion generate to be sure to match with mocked service response
            mock_generate_request_id.return_value = NUMQUESTION

            # mock service response
            expected_content = (
                "NUMTRANS=0034813563&NUMAPPEL=0061548226&"
                f"NUMQUESTION={NUMQUESTION}&SITE={PAYBOX_SITE}&RANG={PAYBOX_RANGE}&"
                "AUTORISATION=XXXXXX&"
                "CODEREPONSE=00000&COMMENTAIRE=Demande trait\xe9e avec succ\xe8s&"
                f"REFABONNE={future_credit_card_uid}&"
                f"PORTEUR={PAYMENT_TOKEN}"
            )
            mock_call_service.return_value = make_mock_response(200, expected_content)

            # now call service to register a new credit card
            with self.assertLogs(logging.getLogger(), level="INFO") as logs:
                payment_backend = backends.get_backend()
                uid, token = payment_backend.register_credit_card(
                    card_number=CREDIT_CARD_DATA["card_number"],
                    cryptogram=CREDIT_CARD_DATA["cryptogram"],
                    expiration_date=CREDIT_CARD_DATA["expiration_date"],
                )
                self.assertTrue("successfully registered" in logs.output[0])
                self.assertIsInstance(uid, uuid.UUID)
                self.assertEqual(uid, future_credit_card_uid)
                self.assertEqual(token, PAYMENT_TOKEN)

    @patch.object(Paybox, "_call_service")
    @patch.object(Paybox, "_generate_request_id")
    def test_oneclick_payment(self, mock_generate_request_id, mock_call_service):
        """Test oneclick payment with registered credit card"""

        # first create a credit card
        month, year = CREDIT_CARD_DATA["expiration_date"].split("/")
        credit_card = factories.CreditCardFactory.create(
            uid=uuid.uuid4(),
            token=PAYMENT_TOKEN,
            last_numbers=CREDIT_CARD_DATA["card_number"][-4:],
            expiration_date=datetime.date(
                int(year),
                int(month),
                monthrange(int(year), int(month))[1],  # last day
            ),
        )

        # mock numquestion generate to be sure to match with mocked service response
        mock_generate_request_id.return_value = NUMQUESTION

        # mock service response
        expected_content = (
            "NUMTRANS=0034813567&NUMAPPEL=0061548235&"
            f"NUMQUESTION={NUMQUESTION}&SITE={PAYBOX_SITE}&RANG={PAYBOX_RANGE}&"
            "AUTORISATION=XXXXXX&"
            "CODEREPONSE=00000&COMMENTAIRE=Demande trait\xe9e avec succ\xe8s&"
            f"REFABONNE={credit_card.uid}&"
            f"PORTEUR={PAYMENT_TOKEN}"
        )
        mock_call_service.return_value = make_mock_response(200, expected_content)

        # now call service to pay with registered credit card
        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            payment_backend = backends.get_backend()
            payment_backend.request_oneclick_payment(
                credit_card,
                decimal.Decimal(19.90),
                uuid.uuid4(),
            )
            self.assertTrue("succeeded" in logs.output[0])
            self.assertTrue(str(credit_card.uid) in logs.output[0])

    @patch.object(Paybox, "_call_service")
    @patch.object(Paybox, "_generate_request_id")
    def test_remove_credit_card(self, mock_generate_request_id, mock_call_service):
        """Test remove registered credit card"""

        # first create a credit card
        month, year = CREDIT_CARD_DATA["expiration_date"].split("/")
        credit_card = factories.CreditCardFactory.create(
            uid=uuid.uuid4(),
            token=PAYMENT_TOKEN,
            last_numbers=CREDIT_CARD_DATA["card_number"][-4:],
            expiration_date=datetime.date(
                int(year),
                int(month),
                monthrange(int(year), int(month))[1],  # last day
            ),
        )

        # mock numquestion generate to be sure to match with mocked service response
        mock_generate_request_id.return_value = NUMQUESTION

        # mock service response
        expected_content = (
            "NUMTRANS=0000000000&NUMAPPEL=0000000000&"
            f"NUMQUESTION={NUMQUESTION}&SITE={PAYBOX_SITE}&RANG={PAYBOX_RANGE}&"
            "AUTORISATION=&"
            "CODEREPONSE=00000&COMMENTAIRE=Demande trait\xe9e avec succ\xe8s&"
            f"REFABONNE={credit_card.uid}&"
            f"PORTEUR={PAYMENT_TOKEN}"
        )
        mock_call_service.return_value = make_mock_response(200, expected_content)

        # now call service to remove credit card
        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            payment_backend = backends.get_backend()
            payment_backend.remove_credit_card(credit_card)
            self.assertTrue("succeeded" in logs.output[0])

    @patch.object(Paybox, "_call_service")
    @patch.object(Paybox, "_generate_request_id")
    def test_remove_credit_card_failure_service(
        self, mock_generate_request_id, mock_call_service
    ):
        """Test manage not found credit card payment service side"""
        # first create a credit card
        month, year = CREDIT_CARD_DATA["expiration_date"].split("/")
        credit_card = factories.CreditCardFactory.create(
            uid=uuid.uuid4(),
            token=PAYMENT_TOKEN,
            last_numbers=CREDIT_CARD_DATA["card_number"][-4:],
            expiration_date=datetime.date(
                int(year),
                int(month),
                monthrange(int(year), int(month))[1],  # last day
            ),
        )

        # mock numquestion generate to be sure to match with mocked service response
        mock_generate_request_id.return_value = NUMQUESTION

        # mock service response
        expected_content = (
            "NUMTRANS=0000000000&NUMAPPEL=0000000000&"
            f"NUMQUESTION={NUMQUESTION}&SITE={PAYBOX_SITE}&RANG={PAYBOX_RANGE}&"
            "AUTORISATION=&"
            "CODEREPONSE=00017&COMMENTAIRE=PAYBOX : Abonn\xe9 inexistant&"
            f"REFABONNE={credit_card.uid}&"
            "PORTEUR={credit_card.token}"
        )
        mock_call_service.return_value = make_mock_response(200, expected_content)

        # now call service to remove credit card
        with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
            payment_backend = backends.get_backend()
            self.assertRaises(
                backends.PaymentServiceError,
                payment_backend.remove_credit_card,
                credit_card,
            )
            self.assertTrue("failed" in logs.output[0])
            self.assertTrue("00017" in logs.output[0])

        # mock numquestion generate to be sure to match with mocked service response
        mock_generate_request_id.return_value = NUMQUESTION

        # mock service crazy service response (NUMQUESTION unmatched with data sent)
        expected_content = (
            "NUMTRANS=0000000000&NUMAPPEL=0000000000&"
            f"NUMQUESTION=nawak&SITE={PAYBOX_SITE}&RANG={PAYBOX_RANGE}&"
            "AUTORISATION=&"
            "CODEREPONSE=00000&COMMENTAIRE=Demande trait\xe9e avec succ\xe8s&"
            f"REFABONNE={credit_card.uid}&"
            f"PORTEUR={PAYMENT_TOKEN}"
        )
        mock_call_service.return_value = make_mock_response(200, expected_content)

        # call service to remove credit card
        with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
            payment_backend = backends.get_backend()
            self.assertRaises(
                backends.PaymentServiceError,
                payment_backend.remove_credit_card,
                credit_card,
            )
            self.assertTrue("Consistency check failure" in logs.output[0])
            self.assertTrue("NUMQUESTION" in logs.output[0])
