# pylint: disable=unexpected-keyword-arg,no-value-for-parameter
"""
Sarbacane API client test module.
"""

from unittest.mock import patch
from urllib.parse import quote_plus

from django.conf import settings
from django.http import HttpRequest
from django.test import override_settings

import responses

from joanie.core.factories import UserFactory
from joanie.core.utils.newsletter.sarbacane import Sarbacane
from joanie.tests.base import LoggingTestCase

SARBACANE_CUSTOM_FIELDS = {
    "fields": [
        {
            "id": "field_prenom",
            "caption": "Prénom",
            "type": "text",
        },
        {
            "id": "field_nom",
            "caption": "Nom",
            "type": "text",
        },
    ]
}

SARBACANE_CONTACTS_LIST = [
    {
        "email": "user_1@example.com",
        "blacklistIds": "",
        "attributes": {"field_prenom": "John", "field_nom": "Doe"},
    },
    {
        "email": "user_2@example.com",
        "blacklistIds": "list-id",
        "attributes": {"field_prenom": "Jane", "field_nom": "Smith"},
    },
    {
        "email": "user_3@example.com",
        "blacklistIds": "",
        "attributes": {"field_prenom": "Bob", "field_nom": "Johnson"},
    },
]


@override_settings(
    SARBACANE_API_URL="https://sarbacane.local/api/v1",
    SARBACANE_API_KEY="api-key",
    SARBACANE_ACCOUNT_ID="account-id",
    SARBACANE_COMMERCIAL_NEWSLETTER_LIST_ID="list-id",
    SARBACANE_COMMERCIAL_NEWSLETTER_BLACKLIST_ID="blacklist-id",
)
class SarbacaneTestCase(LoggingTestCase):
    """
    Sarbacane API client test case.
    """

    def setUp(self):
        base_url = settings.SARBACANE_API_URL
        list_id = settings.SARBACANE_COMMERCIAL_NEWSLETTER_LIST_ID
        blacklist_id = settings.SARBACANE_COMMERCIAL_NEWSLETTER_BLACKLIST_ID
        self.url_api = f"{base_url}/lists/{list_id}"
        self.url_list_contacts = f"{self.url_api}/contacts"
        self.url_subscribe_to_list = f"{self.url_list_contacts}/upsert"
        self.url_custom_fields = f"{self.url_api}/fields"
        self.url_list_unsubscribers = (
            f"{base_url}/blacklists/{blacklist_id}/unsubscribers"
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_subscribe_to_commercial_list_ok(self):
        """
        Test the addition of a contact to the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        # First, mock the custom fields request
        responses.add(
            responses.GET,
            self.url_custom_fields,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json=SARBACANE_CUSTOM_FIELDS,
        )

        # Then, mock the subscribe request
        json_response = {"success": True}
        responses.add(
            responses.POST,
            self.url_subscribe_to_list,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "email": user.email,
                        "field_prenom": user.first_name,
                        "field_nom": user.last_name,
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.subscribe_to_commercial_list()

        self.assertEqual(json_response, response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Adding email for user {user.id} to list list-id",
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_subscribe_to_commercial_list_failed(self):
        """
        Test the addition of a contact to the commercial newsletter list when it fails.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        # First, mock the custom fields request
        responses.add(
            responses.GET,
            self.url_custom_fields,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json=SARBACANE_CUSTOM_FIELDS,
        )

        # Then, mock the subscribe request with an error
        responses.add(
            responses.POST,
            self.url_subscribe_to_list,
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "email": user.email,
                        "field_prenom": user.first_name,
                        "field_nom": user.last_name,
                    }
                ),
            ],
            status=400,
            json={"error": "Invalid parameter"},
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            sarbacane_user.subscribe_to_commercial_list()

        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Adding email for user {user.id} to list list-id",
                ),
                (
                    "ERROR",
                    f"Error calling Sarbacane API {self.url_subscribe_to_list}"
                    ' | 400: {"error": "Invalid parameter"}',
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_unsubscribe_from_commercial_list_ok(self):
        """
        Test the removal of a contact from the commercial newsletter list.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.DELETE,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json={"success": True},
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.unsubscribe_from_commercial_list()

        self.assertTrue(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Removing email for user {user.id} from list list-id",
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_unsubscribe_from_commercial_list_failed(self):
        """
        Test the removal of a contact from the commercial newsletter list when it fails.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.DELETE,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=400,
            json={"error": "Contact not found"},
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.unsubscribe_from_commercial_list()

        self.assertIsNone(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Removing email for user {user.id} from list list-id",
                ),
                (
                    "ERROR",
                    (
                        f"Error calling Sarbacane API {self.url_list_contacts}"
                        f"?email={email_url_encoded}"
                        ' | 400: {"error": "Contact not found"}'
                    ),
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_has_unsubscribed_from_commercial_newsletter_true(self):
        """
        Test checking if a contact has unsubscribed from the commercial newsletter list (true case).
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.GET,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json=[
                {
                    "email": user.email,
                    "blacklistIds": settings.SARBACANE_COMMERCIAL_NEWSLETTER_BLACKLIST_ID,
                }
            ],
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.has_unsubscribed_from_commercial_newsletter()

        self.assertTrue(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Checking if user {user.id} has unsubscribed from list list-id",
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_has_unsubscribed_from_commercial_newsletter_false(self):
        """
        Test checking if a contact has unsubscribed from
        the commercial newsletter list (false case).
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.GET,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json=[
                {
                    "email": user.email,
                    "blacklistIds": "",
                }
            ],
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.has_unsubscribed_from_commercial_newsletter()

        self.assertFalse(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Checking if user {user.id} has unsubscribed from list list-id",
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_has_unsubscribed_from_commercial_newsletter_other_blacklist(self):
        """
        Test checking if a contact has unsubscribed from
        the commercial newsletter list. If the user is registered in a blacklist,
        but not the one of the commercial newsletter list, the function should return False.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.GET,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json=[
                {
                    "email": user.email,
                    "blacklistIds": "blacklist-other-id",
                }
            ],
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.has_unsubscribed_from_commercial_newsletter()

        self.assertFalse(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Checking if user {user.id} has unsubscribed from list list-id",
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_has_unsubscribed_from_commercial_newsletter_no_contact(self):
        """
        Test checking if a contact has unsubscribed when the contact doesn't exist.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.GET,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json=[],
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.has_unsubscribed_from_commercial_newsletter()

        self.assertFalse(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Checking if user {user.id} has unsubscribed from list list-id",
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_has_unsubscribed_from_commercial_newsletter_error(self):
        """
        Test checking if a contact has unsubscribed when the API returns an error.
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        email_url_encoded = quote_plus(user.email)
        responses.add(
            responses.GET,
            f"{self.url_list_contacts}?email={email_url_encoded}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=400,
            json={"error": "Invalid parameter"},
        )

        sarbacane_user = Sarbacane(user.to_dict())

        with self.assertLogs() as logger:
            response = sarbacane_user.has_unsubscribed_from_commercial_newsletter()

        self.assertFalse(response)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Checking if user {user.id} has unsubscribed from list list-id",
                ),
                (
                    "ERROR",
                    (
                        f"Error calling Sarbacane API {self.url_list_contacts}"
                        f"?email={email_url_encoded}"
                        ' | 400: {"error": "Invalid parameter"}'
                    ),
                ),
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    @patch(
        "joanie.core.utils.newsletter.sarbacane.check_commercial_newsletter_subscription_webhook"
    )
    def test_handle_notification_unsubscribe(self, mock_check_subscription):
        """
        Test handling a notification from Sarbacane when a user unsubscribes.
        """
        # Create a mock request with unsubscribe event data
        unsubscriber_id = "1234567890"
        responses.add(
            responses.GET,
            f"{self.url_list_unsubscribers}/{unsubscriber_id}",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "apiKey": settings.SARBACANE_API_KEY,
                        "accountId": settings.SARBACANE_ACCOUNT_ID,
                    }
                ),
            ],
            status=200,
            json={
                "createdAt": "2025-02-27T13:39:11.679142Z",
                "createdBy": "SARBACANE",
                "email": "user@example.com",
                "id": unsubscriber_id,
                "modifiedAt": "2025-03-03T14:11:21.088577Z",
                "modifiedBy": "SARBACANE",
                "phones": "",
                "source": "DEV - Campagne de test",
                "state": "UNSUBSCRIBERS",
            },
        )

        request = HttpRequest()
        request.data = {"ID": unsubscriber_id, "type": "unsubscribe"}

        # Call the handle_notification method
        Sarbacane().handle_notification(request)

        # Check that the webhook was called with the correct email
        mock_check_subscription.delay.assert_called_once_with(["user@example.com"])

    @patch(
        "joanie.core.utils.newsletter.sarbacane.check_commercial_newsletter_subscription_webhook"
    )
    def test_handle_notification_not_unsubscribe(self, mock_check_subscription):
        """
        Test handling a notification from Sarbacane when the event is not an unsubscribe.
        """
        # Create a mock request with a different event type
        request = HttpRequest()
        request.data = {"ID": "1234567890", "type": "open"}

        # Call the handle_notification method
        Sarbacane().handle_notification(request)

        # Check that the webhook was not called
        mock_check_subscription.delay.assert_not_called()

    @responses.activate(assert_all_requests_are_fired=True)
    @patch(
        "joanie.core.utils.newsletter.sarbacane.check_commercial_newsletter_subscription_webhook"
    )
    def test_handle_notification_unknown_subscriber_id(self, mock_check_subscription):
        """
        Test handling a notification from Sarbacane when the subscriber ID is not found.
        """

        responses.add(
            responses.GET,
            f"{self.url_list_unsubscribers}/unknown-subscriber-id",
            status=404,
            json={"message": "CONTACT_NOT_FOUND"},
        )

        request = HttpRequest()
        request.data = {"ID": "unknown-subscriber-id", "type": "unsubscribe"}

        # Call the handle_notification method
        with self.assertLogs() as logger:
            Sarbacane().handle_notification(request)

        # Check that the webhook was not called
        mock_check_subscription.delay.assert_not_called()
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    (
                        "Error calling Sarbacane API "
                        f"{self.url_list_unsubscribers}/unknown-subscriber-id"
                        ' | 404: {"message": "CONTACT_NOT_FOUND"}'
                    ),
                )
            ],
        )
