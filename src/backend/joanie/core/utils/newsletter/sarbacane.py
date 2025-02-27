# pylint: disable=too-many-instance-attributes
"""
Sarbacane API client.
"""

import logging

from django.conf import settings

import requests

from joanie.core.utils.newsletter.base import NewsletterClient
from joanie.core.utils.newsletter.subscription import (
    check_commercial_newsletter_subscription_webhook,
)

logger = logging.getLogger(__name__)


class Sarbacane(NewsletterClient):
    """
    Sarbacane API client.
    """

    name = "Sarbacane"
    custom_fields_mapping = {
        "Prénom": "first_name",
        "Nom": "last_name",
    }

    def __init__(self, user=None):
        self.list_id = settings.SARBACANE_COMMERCIAL_NEWSLETTER_LIST_ID
        self.blacklist_id = settings.SARBACANE_COMMERCIAL_NEWSLETTER_BLACKLIST_ID
        self.url_api = settings.SARBACANE_API_URL
        self.url_lists = f"{self.url_api}/lists/{self.list_id}"
        self.url_list_contacts = f"{self.url_lists}/contacts"
        self.url_subscribe_to_list = f"{self.url_list_contacts}/upsert"
        self.url_unsubscribe_from_list = self.url_list_contacts
        self.url_custom_fields = f"{self.url_lists}/fields"
        self.url_list_unsubscribers = (
            f"{self.url_api}/blacklists/{self.blacklist_id}/unsubscribers"
        )
        self.headers = {
            "content-type": "application/json",
            "apiKey": settings.SARBACANE_API_KEY,
            "accountId": settings.SARBACANE_ACCOUNT_ID,
        }

        super().__init__(user)

    def _log_info(self, message):
        """Log an info message."""
        logger.info(message, self.user.get("id"), self.list_id)

    def _call_api(
        self,
        url,
        method="GET",
        payload=None,
        query_params=None,
        log_level=logging.ERROR,
    ):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """
        Call the Sarbacane API with the given payload.
        """
        if method == "POST":
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
        elif method == "DELETE":
            response = requests.delete(
                url, params=query_params, json=payload, headers=self.headers, timeout=5
            )
        else:
            response = requests.get(
                url, params=query_params, headers=self.headers, timeout=5
            )

        return self._check_response_api(response, log_level)

    def _get_custom_fields(self):
        """
        Get the custom field ids.
        """
        response = self._call_api(self.url_custom_fields)
        custom_fields = response.json().get("fields", [])

        return {
            field["caption"]: field["id"]
            for field in custom_fields
            if field["caption"] in self.custom_fields_mapping
        }

    def subscribe_to_commercial_list(self):
        """
        Add/Update a contact to the commercial newsletter list.
        """
        self._log_info("Adding email for user %s to list %s")
        payload = {"email": self.user.get("email")}

        custom_fields = self._get_custom_fields()
        for field_caption, field_id in custom_fields.items():
            user_field = self.custom_fields_mapping.get(field_caption)
            payload[field_id] = self.user.get(user_field)

        response = self._call_api(self.url_subscribe_to_list, "POST", payload)

        return response.json()

    def unsubscribe_from_commercial_list(self):
        """
        Remove a contact from the commercial newsletter list.
        """
        self._log_info("Removing email for user %s from list %s")
        response = self._call_api(
            self.url_unsubscribe_from_list,
            "DELETE",
            query_params={"email": self.user.get("email")},
        )
        if not response.ok:
            return None

        return True

    def has_unsubscribed_from_commercial_newsletter(self):
        """
        Check if a contact has unsubscribed from the commercial newsletter list.
        If this is the case, the contact has been added to the commercial newsletter blacklist.
        """
        self._log_info("Checking if user %s has unsubscribed from list %s")

        response = self._call_api(
            self.url_list_contacts, query_params={"email": self.user.get("email")}
        )

        content = response.json()

        if not response.ok or content is None:
            return False

        return any(
            self.blacklist_id in contact.get("blacklistIds") for contact in content
        )

    def _get_unsubscriber(self, unsubscriber_id: str) -> dict:
        """
        Get an unsubscriber from the blacklist.
        """
        response = self._call_api(f"{self.url_list_unsubscribers}/{unsubscriber_id}")

        if not response.ok:
            return None

        return response.json()

    def handle_notification(self, request):
        """
        Handle a notification from the newsletter client.
        """
        event = request.data
        if (unsubscriber_id := event.get("ID")) and event["type"] == "unsubscribe":
            unsubcriber = self._get_unsubscriber(unsubscriber_id)
            if unsubcriber:
                check_commercial_newsletter_subscription_webhook.delay(
                    [unsubcriber["email"]],
                )
