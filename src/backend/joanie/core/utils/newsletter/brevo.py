"""
Brevo API client.
"""

import logging

from django.conf import settings

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


class Brevo:
    """
    Brevo API client.
    """

    def __init__(self):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY
        self.api_instance = sib_api_v3_sdk.ContactsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        self.contact_emails = sib_api_v3_sdk.AddContactToList()
        self.list_id = settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID

    def create_contact_to_commercial_list(self, user):
        """
        Create a contact with the given email, and add it to the commercial newsletter list.
        """
        logger.info(
            "Creating contact with email for user %s in list %s",
            user.id,
            self.list_id,
        )
        try:
            create_contact = sib_api_v3_sdk.CreateContact(
                email=user.email, list_ids=[self.list_id]
            )
            return self.api_instance.create_contact(create_contact)
        except ApiException as e:
            logger.exception(
                "Error creating contact with email for user %s in list %s",
                user.id,
                self.list_id,
                extra={
                    "context": {"user_id": user.id, "list_id": self.list_id, "error": e}
                },
            )
        return None

    def add_contact_to_commercial_list(self, user):
        """
        Add a contact to the commercial newsletter list.
        """
        logger.info("Adding email for user %s to list %s", user.id, self.list_id)
        self.contact_emails.emails = [user.email]
        try:
            return self.api_instance.add_contact_to_list(
                list_id=self.list_id,
                contact_emails=self.contact_emails,
            )
        except ApiException as e:
            logger.exception(
                "Error adding email for user %s to list %s",
                user.id,
                self.list_id,
                extra={
                    "context": {"user_id": user.id, "list_id": self.list_id, "error": e}
                },
            )
            # return self.create_contact_to_commercial_list(user)
            return None

    def remove_contact_from_commercial_list(self, user):
        """
        Remove a contact from the commercial newsletter list.
        """
        logger.info("Removing email for user %s from list %s", user.id, self.list_id)
        self.contact_emails.emails = [user.email]
        try:
            return self.api_instance.remove_contact_from_list(
                list_id=self.list_id,
                contact_emails=self.contact_emails,
            )
        except ApiException as e:
            logger.exception(
                "Error removing email for user %s from list %s",
                user.id,
                self.list_id,
                extra={
                    "context": {"user_id": user.id, "list_id": self.list_id, "error": e}
                },
            )
        return None
