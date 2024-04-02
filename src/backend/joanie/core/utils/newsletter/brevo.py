# pylint: disable=too-many-instance-attributes
"""
Brevo API client.
"""

import logging
from http.client import BAD_REQUEST
from urllib.parse import quote_plus

from django.conf import settings
from django.urls import reverse

import requests

logger = logging.getLogger(__name__)


class Brevo:
    """
    Brevo API client.
    """

    def __init__(self, user=None):
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": settings.BREVO_API_KEY,
        }

        self.list_id = settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID
        self.user = user or {}

        self.api_url = settings.BREVO_API_URL
        self.contact_url = f"{self.api_url}contacts"
        self.list_contacts_url = f"{self.api_url}contacts/lists/{self.list_id}/contacts"
        self.subscribe_to_list_url = f"{self.list_contacts_url}/add"
        self.unsubscribe_from_list_url = f"{self.list_contacts_url}/remove"

    def _log_info(self, message):
        """Log an info message."""
        logger.info(message, self.user.get("id"), self.list_id)

    def _call_api(self, url, payload=None, query_params=None):
        """
        Call the Brevo API with the given payload.
        """
        if payload:
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
        else:
            response = requests.get(
                url, params=query_params, headers=self.headers, timeout=5
            )
        if not response.ok:
            logger.error(
                "Error calling Brevo API %s | %s: %s",
                url,
                response.status_code,
                response.text,
                extra={
                    "context": {
                        "user_id": self.user.get("id"),
                        "list_id": self.list_id,
                        "url": url,
                        "response": response.text,
                    }
                },
            )
        return response

    def create_contact_to_commercial_list(self):
        """
        Create a contact with the given email, and add it to the commercial newsletter list.
        """
        self._log_info("Creating contact with email for user %s in list %s")

        payload = {
            "email": self.user.get("email"),
            "attributes": {
                "NOM": self.user.get("last_name"),
                "PRENOM": self.user.get("first_name"),
            },
            "listIds": [self.list_id],
        }
        response = self._call_api(self.contact_url, payload)
        if not response.ok:
            return None

        return response.json()

    def subscribe_to_commercial_list(self):
        """
        Add a contact to the commercial newsletter list.
        """
        self._log_info("Adding email for user %s to list %s")

        payload = {"emails": [self.user.get("email")]}
        response = self._call_api(self.subscribe_to_list_url, payload)
        if not response.ok:
            if (
                response.status_code == BAD_REQUEST
                and response.json().get("code") == "invalid_parameter"
            ):
                return self.create_contact_to_commercial_list()
            return None

        return response.json()

    def unsubscribe_from_commercial_list(self):
        """
        Remove a contact from the commercial newsletter list.
        """
        self._log_info("Removing email for user %s from list %s")

        payload = {"emails": [self.user.get("email")]}
        response = self._call_api(self.unsubscribe_from_list_url, payload)
        if not response.ok:
            return None

        return response.json()

    def has_unsubscribed_from_commercial_newsletter(self):
        """
        Check if a contact has unsubscribed from the commercial newsletter list.
        """
        self._log_info("Checking if user %s has unsubscribed from list %s")

        email_url_encoded = quote_plus(self.user.get("email"))
        response = self._call_api(f"{self.contact_url}/{email_url_encoded}")
        if not response.ok:
            return False

        list_unsubscribed = response.json().get("listUnsubscribed")
        return settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID in list_unsubscribed

    def create_webhook(
        self, base_url, description="Webhook triggered on unsubscription"
    ):
        """
        Create a webhook for the Brevo API.
        """
        webook_url = base_url + reverse("commercial_newsletter_subscription_webhook")
        logger.info("Webhook endpoint %s", webook_url)

        url = f"{self.api_url}webhooks"

        payload = {
            "type": "marketing",
            "auth": {
                "type": "bearer",
                "token": settings.BREVO_WEBHOOK_TOKEN,
            },
            "events": ["unsubscribed"],
            "url": webook_url,
            "description": description,
            "batched": True,
        }

        response = self._call_api(url, payload)

        if not response.ok:
            return None

        webhook_id = response.json().get("id")
        logger.info("Webhook created %s", webhook_id)
        return webhook_id

    def get_contacts_count(self):
        """
        Get the count of contacts in the commercial newsletter list.
        """
        return self.get_contacts(limit=1)

    def get_contacts(self, limit=500, offset=0):
        """
        Get contacts from the commercial newsletter list.

        If limit is 1, return the count of contacts.
        """
        response = self._call_api(
            self.list_contacts_url,
            query_params={"limit": limit, "offset": offset, "sort": "desc"},
        )

        if not response.ok:
            return None

        if limit == 1:
            return response.json().get("count")
        return response.json().get("contacts")
