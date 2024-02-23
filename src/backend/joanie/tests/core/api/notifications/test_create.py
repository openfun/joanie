"""
Test suite for Notification create API endpoint.
"""
from http import HTTPStatus
from unittest.mock import patch

from django.test import override_settings

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


@override_settings(JOANIE_NOTIFICATION_SECRETS=["shared secret"])
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

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(models.Notification.objects.count(), 0)

    def test_api_notification_create_user(self):
        """
        User should not be able to create notifications
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)
        data = {
            "message": "Test message",
            "level": "info",
        }

        response = self.client.post(
            "/api/v1.0/notifications/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(models.Notification.objects.count(), 0)

    # @patch(signature, "generate_signature")
    @patch("joanie.core.api.client.check_signature")
    def test_api_notification_create_authorized_token(self, mock_check_signature):
        """
        Authorized token should be able to create notifications
        """
        mock_check_signature.return_value = None
        user = factories.UserFactory()
        data = {
            "user_id": user.id,
            "message": "Test message",
            "level": "info",
        }

        response = self.client.post(
            "/api/v1.0/notifications/",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Notification.objects.count(), 1)
        notification = models.Notification.objects.first()
        self.assertEqual(notification.message, "Test message")
        self.assertEqual(notification.level, "info")
        self.assertEqual(notification.read, False)
        self.assertEqual(notification.user, user)
