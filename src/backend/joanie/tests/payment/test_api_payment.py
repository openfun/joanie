"""Test suite for the payment api"""
from unittest import mock

from django.test.utils import override_settings

from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.exceptions import ParseNotificationFailed
from joanie.tests.base import BaseAPITestCase


@override_settings(
    JOANIE_PAYMENT_BACKEND={
        "backend": "joanie.payment.backends.dummy.DummyPaymentBackend"
    }
)
class PaymentApiTestCase(BaseAPITestCase):
    """Test case for the Payment Api"""

    @mock.patch.object(DummyPaymentBackend, "handle_notification")
    def test_api_payment_handle_notification_failed(self, mock_notification):
        """
        When a notification cannot be handled a bad request response should be
        returned.
        """
        mock_notification.side_effect = ParseNotificationFailed(
            "Payment does not exist"
        )

        response = self.client.post(
            "/api/payments/notifications",
            content_type="application/json",
            data={"id": "pay_0000"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, "Payment does not exist")
        mock_notification.assert_called_once()

    @mock.patch.object(DummyPaymentBackend, "handle_notification")
    def test_api_payment_handle_notification(self, mock_notification):
        """
        When a notification is handled with success, an empty OK response should
        be returned.
        """

        response = self.client.post(
            "/api/payments/notifications",
            content_type="application/json",
            data={"id": "pay_0000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)
        mock_notification.assert_called_once()
