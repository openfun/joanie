"""
Test suite for ActivityLog update API endpoint.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ActivityLogUpdateApiTest(BaseAPITestCase):
    """
    Test suite for ActivityLog update API endpoint.
    """

    def test_api_activity_log_update_anonymous(self):
        """
        Anonymous users should not access activity log details
        """
        activity_log = factories.ActivityLogFactory()
        response = self.client.put(f"/api/v1.0/activity-logs/{activity_log.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_activity_log_update_no_activity_logs(self):
        """
        User should not access activity log details
        """
        user = factories.UserFactory()
        activity_log = factories.ActivityLogFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.put(
            f"/api/v1.0/activity-logs/{activity_log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_activity_log_update_with_activity_logs(self):
        """
        User should not access their activity log details
        """
        user = factories.UserFactory()
        activity_log = factories.ActivityLogFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.put(
            f"/api/v1.0/activity-logs/{activity_log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
