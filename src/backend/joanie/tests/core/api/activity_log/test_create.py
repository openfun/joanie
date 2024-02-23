"""
Test suite for ActivityLog create API endpoint.
"""

from http import HTTPStatus
from unittest.mock import patch
from uuid import uuid4

from django.test import override_settings

from joanie.core.enums import (
    ACTIVITY_LOG_LEVEL_INFO,
    ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
)
from joanie.core.factories import UserFactory
from joanie.core.models import ActivityLog
from joanie.tests.base import BaseAPITestCase


@override_settings(JOANIE_ACTIVITY_LOG_SECRETS=["shared secret"])
class ActivityLogCreateApiTest(BaseAPITestCase):
    """
    Test suite for ActivityLog create API endpoint.
    """

    def test_api_activity_log_create_anonymous(self):
        """
        Anonymous users should not be able to get activity logs
        """
        data = {
            "type": ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
            "level": ACTIVITY_LOG_LEVEL_INFO,
        }
        response = self.client.post(
            "/api/v1.0/activity-logs/", data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(ActivityLog.objects.count(), 0)

    def test_api_activity_log_create_user(self):
        """
        User should not be able to create activity logs
        """
        user = UserFactory()
        jwt_token = self.generate_token_from_user(user)
        data = {
            "type": ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
            "level": ACTIVITY_LOG_LEVEL_INFO,
        }

        response = self.client.post(
            "/api/v1.0/activity-logs/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(ActivityLog.objects.count(), 0)

    @patch("joanie.core.api.client.check_signature")
    def test_api_activity_log_create_authorized_token(self, mock_check_signature):
        """
        Authorized token should be able to create activity logs
        """
        mock_check_signature.return_value = None
        user = UserFactory()
        data = {
            "user_id": str(user.id),
            "type": ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
            "level": ACTIVITY_LOG_LEVEL_INFO,
            "context": {"order_id": uuid4()},
        }

        response = self.client.post(
            "/api/v1.0/activity-logs/",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(ActivityLog.objects.count(), 1)
        activity_log = ActivityLog.objects.first()
        self.assertEqual(activity_log.level, "info")
        self.assertEqual(activity_log.user, user)
