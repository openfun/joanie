"""
Test suite for Notification create API endpoint.
"""
from http import HTTPStatus

from joanie.tests.base import BaseAPITestCase


class NotificationCreateApiTest(BaseAPITestCase):
    """
    Test suite for Notification create API endpoint.
    """

    def test_api_notification_create_anonymous(self):
        """
        Anonymous users should not be able to get notifications
        """
        data = {
            "message": "Test message",
            "level": "info",
        }
        response = self.client.post(
            "/api/v1.0/notifications/", data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
