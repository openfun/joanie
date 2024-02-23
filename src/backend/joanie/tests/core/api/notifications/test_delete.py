"""
Test suite for Notification delete API endpoint.
"""
from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class NotificationDeleteApiTest(BaseAPITestCase):
    """
    Test suite for Notification delete API endpoint.
    """

    def test_api_notification_delete_anonymous(self):
        """
        Anonymous users should not delete notification
        """
        notification = factories.NotificationFactory()
        response = self.client.delete(f"/api/v1.0/notifications/{notification.id}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

    def test_api_notification_delete_no_notifications(self):
        """
        User should not delete not owned notification
        """
        user = factories.UserFactory()
        notification = factories.NotificationFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/notifications/{notification.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_notification_delete_with_notifications(self):
        """
        User should not access their notification details
        """
        user = factories.UserFactory()
        notification = factories.NotificationFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/notifications/{notification.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(models.Notification.objects.count(), 0)
