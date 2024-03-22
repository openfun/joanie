"""
Test suite for ActivityLog list API endpoint.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class ActivityLogListApiTest(BaseAPITestCase):
    """
    Test suite for ActivityLog list API endpoint.
    """

    def test_api_activity_log_list_anonymous(self):
        """
        Anonymous users should not be able to get activity logs
        """
        factories.ActivityLogFactory()
        response = self.client.get("/api/v1.0/activity-logs/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_activity_log_list_user(self):
        """
        User should see only their activity logs
        """
        user = factories.UserFactory()
        user_activity_logs = factories.ActivityLogFactory.create_batch(3, user=user)
        factories.ActivityLogFactory.create_batch(2)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/activity-logs/",
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
                        "id": str(activity_log.id),
                        "user_id": str(activity_log.user.id),
                        "level": activity_log.level,
                        "created_on": format_date(activity_log.created_on),
                        "type": activity_log.type,
                        "context": activity_log.context,
                    }
                    for activity_log in user_activity_logs
                ],
            },
        )
