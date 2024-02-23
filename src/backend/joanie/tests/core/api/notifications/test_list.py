"""
Test suite for Notification list API endpoint.
"""
from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class NotificationListApiTest(BaseAPITestCase):
    """
    Test suite for Notification list API endpoint.
    """

    def test_api_notification_list_anonymous(self):
        """
        Anonymous users should not be able to get notifications
        """
        factories.NotificationFactory()
        response = self.client.get("/api/v1.0/notifications/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_notification_list_user(self):
        """
        User should see only their notifications
        """
        user = factories.UserFactory()
        user_notifications = factories.NotificationFactory.create_batch(3, user=user)
        factories.NotificationFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/notifications/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(notification.id),
                        "user_id": str(notification.user.id),
                        "message": notification.message,
                        "level": notification.level,
                        "read": notification.read,
                        "created_on": format_date(notification.created_on),
                    }
                    for notification in user_notifications
                ],
            },
        )
