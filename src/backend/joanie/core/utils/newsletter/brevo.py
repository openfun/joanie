"""
Brevo API client.
"""

import logging
from http.client import BAD_REQUEST

from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class Brevo:
    """
    Brevo API client.
    """

    def __init__(self, user):
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": settings.BREVO_API_KEY,
        }

        self.list_id = settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID
        self.user = user

        api_url = settings.BREVO_API_URL
        self.contact_url = f"{api_url}contacts"
        list_contacts_url = f"{api_url}contacts/lists/{self.list_id}/contacts"
        self.subscribe_to_list_url = f"{list_contacts_url}/add"
        self.unsubscribe_from_list_url = f"{list_contacts_url}/remove"

    def _log_info(self, message):
        """Log an info message."""
        logger.info(message, self.user.id, self.list_id)

    def _call_api(self, url, payload):
        """
        Call the Brevo API with the given payload.
        """
        response = requests.post(url, json=payload, headers=self.headers, timeout=5)
        if not response.ok:
            logger.error(
                "Error calling Brevo API %s %s",
                url,
                response,
                extra={
                    "context": {
                        "user_id": self.user.id,
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

        payload = {"email": self.user.email, "listIds": [self.list_id]}
        response = self._call_api(self.contact_url, payload)
        if not response.ok:
            return None

        return response.json()

    def subscribe_to_commercial_list(self):
        """
        Add a contact to the commercial newsletter list.
        """
        self._log_info("Adding email for user %s to list %s")

        payload = {"emails": [self.user.email]}
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

        payload = {"emails": [self.user.email]}
        response = self._call_api(self.unsubscribe_from_list_url, payload)
        if response.ok:
            return response.json()
        return None
