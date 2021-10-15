"""get_payment_backend() test suite"""

from django.test import TestCase
from django.test.utils import override_settings

from joanie.payment import get_payment_backend
from joanie.payment.backends.dummy import DummyPaymentBackend


class GetPaymentBackendTestSuite(TestCase):
    """Test suite for the get_payment_backend method"""

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.payment.backends.dummy.DummyPaymentBackend",
        }
    )
    def test_get_payment_backend_get_backend(self):
        """
        When JOANIE_PAYMENT_BACKEND is well configured,
        a payment backend should be returned.
        """
        backend = get_payment_backend()
        self.assertEqual(backend.name, "dummy")
        self.assertIsInstance(backend, DummyPaymentBackend)

    @override_settings(JOANIE_PAYMENT_BACKEND=None)
    def test_get_payment_backend_raises_error_when_configuration_is_missing(self):
        """
        When JOANIE_PAYMENT_BACKEND is not defined, ValueError exception should be raised.
        """
        with self.assertRaises(ValueError) as context:
            get_payment_backend()

        self.assertEqual(
            str(context.exception),
            (
                "Cannot instantiate a payment backend. "
                "JOANIE_PAYMENT_BACKEND configuration seems not valid. Check your settings.py."
            ),
        )

    @override_settings(
        JOANIE_PAYMENT_BACKEND={"BACKEND": "joanie.payment.backends.unknown"}
    )
    def test_get_payment_backend_raises_error_when_backend_is_unknown(self):
        """
        When JOANIE_PAYMENT_BACKEND is unknown, ValueError exception should be raised.
        """
        with self.assertRaises(ValueError) as context:
            get_payment_backend()

        self.assertEqual(
            str(context.exception),
            (
                "Cannot instantiate a payment backend. "
                "JOANIE_PAYMENT_BACKEND configuration seems not valid. Check your settings.py."
            ),
        )

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.payment.backends.payplug.PayplugBackend"
        }
    )
    def test_get_payment_backend_raises_error_when_backend_is_misconfigured(self):
        """
        When JOANIE_PAYMENT_BACKEND is misconfigured, ValueError exception should be raised.
        """
        with self.assertRaises(ValueError) as context:
            get_payment_backend()

        self.assertEqual(
            str(context.exception),
            (
                "Cannot instantiate a payment backend. "
                "JOANIE_PAYMENT_BACKEND configuration seems not valid. Check your settings.py."
            ),
        )
