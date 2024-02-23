"""
Test suite for ActivityLog retrieve API endpoint.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ActivityLogRetrieveApiTest(BaseAPITestCase):
    """
    Test suite for ActivityLog retrieve API endpoint.
    """

    def test_api_activity_log_retrieve_anonymous(self):
        """
        Anonymous users should not access activity log details
        """
        activity_log = factories.ActivityLogFactory()
        response = self.client.get(f"/api/v1.0/activity-logs/{activity_log.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_activity_log_retrieve_no_activity_logs(self):
        """
        User should not access activity log details
        """
        user = factories.UserFactory()
        activity_log = factories.ActivityLogFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/activity-logs/{activity_log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_activity_log_retrieve_with_activity_logs(self):
        """
        User should not access their activity log details
        """
        user = factories.UserFactory()
        activity_log = factories.ActivityLogFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/activity-logs/{activity_log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
