# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
"""
Test suite for brevo newsletter subscription webhook.
"""

from http import HTTPStatus
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

import responses

from joanie.core.factories import UserFactory
from joanie.tests.base import BaseAPITestCase


class RemoteEndpointsCourseRunApiTest(BaseAPITestCase):
    """Test suite for remote API endpoints on course run."""

    @override_settings(
        JOANIE_AUTHORIZED_API_TOKENS=["auth-token"],
        BREVO_COMMERCIAL_NEWSLETTER_LIST_ID=123456,
    )
    @responses.activate(assert_all_requests_are_fired=True)
    @patch(
        "joanie.core.api.remote_endpoints.check_commercial_newsletter_subscription_webhook"
    )
    def test_commercial_newsletter_subscription_webhook(
        self, mock_check_commercial_newsletter_subscription_webhook
    ):
        """
        The check for unsubscribing is called
        when a user unsubscribes from the commercial newsletter list.
        """
        UserFactory(email="user@example.com")
        response = self.client.post(
            "/api/v1.0/newsletter-webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer auth-token",
            data=[
                {
                    "camp_id": 1120,
                    "campaign name": "Test campaign",
                    "date_event": "2024-03-28 17:20:22",
                    "date_sent": "2024-02-15 07:31:19",
                    "email": "user@example.com",
                    "event": "unsubscribe",
                    "id": 1015471,
                    "list_id": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    "tag": "",
                    "ts": 1711642822,
                    "ts_event": 1711642822,
                    "ts_sent": 1707978679,
                }
            ],
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_check_commercial_newsletter_subscription_webhook.delay.assert_called_once_with(
            ["user@example.com"]
        )

    @override_settings(
        JOANIE_AUTHORIZED_API_TOKENS=["auth-token"],
        BREVO_COMMERCIAL_NEWSLETTER_LIST_ID=123456,
    )
    @responses.activate(assert_all_requests_are_fired=True)
    @patch(
        "joanie.core.api.remote_endpoints.check_commercial_newsletter_subscription_webhook"
    )
    def test_commercial_newsletter_subscription_webhook_other_list(
        self, mock_check_commercial_newsletter_subscription_webhook
    ):
        """
        The check for unsubscribing is not called
        when a user unsubscribes from a list other than the commercial newsletter list.
        """
        response = self.client.post(
            "/api/v1.0/newsletter-webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer auth-token",
            data=[
                {
                    "camp_id": 1120,
                    "campaign name": "Test campaign",
                    "date_event": "2024-03-28 17:20:22",
                    "date_sent": "2024-02-15 07:31:19",
                    "email": "user@example.com",
                    "event": "unsubscribe",
                    "id": 1015471,
                    "list_id": [123],
                    "tag": "",
                    "ts": 1711642822,
                    "ts_event": 1711642822,
                    "ts_sent": 1707978679,
                }
            ],
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_check_commercial_newsletter_subscription_webhook.delay.assert_not_called()

    @override_settings(
        JOANIE_AUTHORIZED_API_TOKENS=["auth-token"],
        BREVO_COMMERCIAL_NEWSLETTER_LIST_ID=123456,
    )
    @responses.activate(assert_all_requests_are_fired=True)
    @patch(
        "joanie.core.api.remote_endpoints.check_commercial_newsletter_subscription_webhook"
    )
    def test_commercial_newsletter_subscription_webhook_other_event(
        self, mock_check_commercial_newsletter_subscription_webhook
    ):
        """
        The check for unsubscribing is not called
        when the event is not an unsubscribe event.
        """
        response = self.client.post(
            "/api/v1.0/newsletter-webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer auth-token",
            data=[
                {
                    "camp_id": 1120,
                    "campaign name": "Test campaign",
                    "date_event": "2024-03-28 17:20:22",
                    "date_sent": "2024-02-15 07:31:19",
                    "email": "user@example.com",
                    "event": "other_event",
                    "id": 1015471,
                    "list_id": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    "tag": "",
                    "ts": 1711642822,
                    "ts_event": 1711642822,
                    "ts_sent": 1707978679,
                }
            ],
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_check_commercial_newsletter_subscription_webhook.delay.assert_not_called()

    @override_settings(
        JOANIE_AUTHORIZED_API_TOKENS=["auth-token"],
        BREVO_COMMERCIAL_NEWSLETTER_LIST_ID=123456,
    )
    @responses.activate(assert_all_requests_are_fired=True)
    @patch(
        "joanie.core.api.remote_endpoints.check_commercial_newsletter_subscription_webhook"
    )
    def test_commercial_newsletter_subscription_webhook_unknown_email(
        self, mock_check_commercial_newsletter_subscription_webhook
    ):
        """
        The check for unsubscribing is not called
        when no user with the given email exists.
        """
        response = self.client.post(
            "/api/v1.0/newsletter-webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer auth-token",
            data=[
                {
                    "camp_id": 1120,
                    "campaign name": "Test campaign",
                    "date_event": "2024-03-28 17:20:22",
                    "date_sent": "2024-02-15 07:31:19",
                    "email": "user@example.com",
                    "event": "unsubscribe",
                    "id": 1015471,
                    "list_id": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                    "tag": "",
                    "ts": 1711642822,
                    "ts_event": 1711642822,
                    "ts_sent": 1707978679,
                }
            ],
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        mock_check_commercial_newsletter_subscription_webhook.delay.assert_not_called()
