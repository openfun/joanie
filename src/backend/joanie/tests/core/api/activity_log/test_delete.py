"""
Test suite for ActivityLog delete API endpoint.
"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class ActivityLogDeleteApiTest(BaseAPITestCase):
    """
    Test suite for ActivityLog delete API endpoint.
    """

    def test_api_activity_log_delete_anonymous(self):
        """
        Anonymous users should not delete activity logs
        """
        activity_log = factories.ActivityLogFactory()
        response = self.client.delete(f"/api/v1.0/activity-logs/{activity_log.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_activity_log_delete_no_activity_logs(self):
        """
        User should not delete not owned activity logs
        """
        user = factories.UserFactory()
        activity_log = factories.ActivityLogFactory()
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/activity-logs/{activity_log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_activity_log_delete_with_activity_logs(self):
        """
        User should not access their activity logs details
        """
        user = factories.UserFactory()
        activity_log = factories.ActivityLogFactory(user=user)
        jwt_token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/activity-logs/{activity_log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
