"""Utility methods for newsletter subscription."""

import logging

from django.apps import apps

from joanie.celery_app import app
from joanie.core.utils.newsletter import get_newsletter_client

logger = logging.getLogger(__name__)


@app.task
def set_commercial_newsletter_subscription(user_dict):
    """
    Set the newsletter subscription for the user.
    """
    if not (newsletter_client := get_newsletter_client()):
        logger.info("No newsletter client configured")
        return None

    client = newsletter_client(user_dict)
    if user_dict.get("has_subscribed_to_commercial_newsletter"):
        logger.info(
            "User %s has subscribed to the commercial newsletter", user_dict.get("id")
        )
        return client.subscribe_to_commercial_list()

    logger.info(
        "User %s has unsubscribed from the commercial newsletter", user_dict.get("id")
    )
    return client.unsubscribe_from_commercial_list()


@app.task
def check_commercial_newsletter_subscription_webhook(emails):
    """
    Check the commercial newsletter subscription status of a user.

    If the contact has unsubscribed from the commercial newsletter list,
    its subscription status will be updated in our database, triggering the removal from the list.
    """
    if not (newsletter_client := get_newsletter_client()):
        logger.info("No newsletter client configured")
        return

    User = apps.get_model("core", "User")  # pylint: disable=invalid-name

    for email in emails:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            continue

        client = newsletter_client(user.to_dict())
        if client.has_unsubscribed_from_commercial_newsletter():
            logger.info(
                "User %s has unsubscribed from the commercial newsletter", user.email
            )
            user.has_subscribed_to_commercial_newsletter = False
            user.save()


@app.task
def synchronize_brevo_subscriptions():
    """
    Synchronize brevo subscriptions.
    """
    list_id = settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID
    User = apps.get_model("core", "User")  # pylint: disable=invalid-name

    # get list of contacts with a limit of 1, just for getting the total count
    brevo = Brevo()
    contacts_count = brevo.get_contacts_count()
    logger.info("Total contacts: %s", contacts_count)

    users_to_update = []

    for offset in range(0, contacts_count, 500):
        contacts = brevo.get_contacts(limit=500, offset=offset)
        logger.info(
            "Processing contacts from %s to %s / %s",
            offset,
            offset + 500,
            contacts_count,
        )
        for contact in contacts:
            try:
                user = User.objects.get(email=contact.get("email"))
            except User.DoesNotExist:
                continue

            updating = False

            if (
                list_id in contact.get("listIds")
                and not user.has_subscribed_to_commercial_newsletter
            ):
                user.has_subscribed_to_commercial_newsletter = True
                updating = True
            elif user.has_subscribed_to_commercial_newsletter:
                user.has_subscribed_to_commercial_newsletter = False
                updating = True

            if updating:
                users_to_update.append(user)
                logger.info(
                    "Updating user %s subscription status to %s",
                    user.id,
                    user.has_subscribed_to_commercial_newsletter,
                )

    users_updated_count = User.objects.bulk_update(
        users_to_update, ["has_subscribed_to_commercial_newsletter"]
    )
    logger.info("Updated %s users", users_updated_count)
