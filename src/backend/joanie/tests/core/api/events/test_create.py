"""
Test suite for Event create API endpoint.
"""
from http import HTTPStatus
from unittest.mock import patch
from uuid import uuid4

from django.test import override_settings

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


@override_settings(JOANIE_EVENT_SECRETS=["shared secret"])
class EventCreateApiTest(BaseAPITestCase):
    """
    Test suite for Event create API endpoint.
    """

    def test_api_event_create_anonymous(self):
        """
        Anonymous users should not be able to get events
        """
        data = {
            "type": enums.EVENT_TYPE_PAYMENT_SUCCEEDED,
            "level": enums.EVENT_INFO,
        }
        response = self.client.post(
            "/api/v1.0/events/", data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(models.Event.objects.count(), 0)

    def test_api_event_create_user(self):
        """
        User should not be able to create events
        """
        user = factories.UserFactory()
        jwt_token = self.generate_token_from_user(user)
        data = {
            "type": enums.EVENT_TYPE_PAYMENT_SUCCEEDED,
            "level": enums.EVENT_INFO,
        }

        response = self.client.post(
            "/api/v1.0/events/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(models.Event.objects.count(), 0)

    @patch("joanie.core.api.client.check_signature")
    def test_api_event_create_authorized_token(self, mock_check_signature):
        """
        Authorized token should be able to create events
        """
        mock_check_signature.return_value = None
        user = factories.UserFactory()
        data = {
            "user_id": str(user.id),
            "type": enums.EVENT_TYPE_PAYMENT_SUCCEEDED,
            "level": enums.EVENT_INFO,
            "context": {"order_id": uuid4()},
        }

        response = self.client.post(
            "/api/v1.0/events/",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Event.objects.count(), 1)
        event = models.Event.objects.first()
        self.assertEqual(event.level, "info")
        self.assertEqual(event.user, user)
