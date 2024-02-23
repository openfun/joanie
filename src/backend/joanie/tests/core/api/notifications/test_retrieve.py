"""
Test suite for Notification retrieve API endpoint.
"""
from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class NotificationRetrieveApiTest(BaseAPITestCase):
    """
    Test suite for Notification retrieve API endpoint.
    """

    def test_api_notification_retrieve_anonymous(self):
        """
        Anonymous users should not access notification details
        """
        notification = factories.NotificationFactory()
        response = self.client.get(f"/api/v1.0/notifications/{notification.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_notification_retrieve_no_notifications(self):
        """
        User should not access notification details
        """
        user = factories.UserFactory()
        notification = factories.NotificationFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/notifications/{notification.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_notification_retrieve_with_notifications(self):
        """
        User should not access their notification details
        """
        user = factories.UserFactory()
        notification = factories.NotificationFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/notifications/{notification.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
