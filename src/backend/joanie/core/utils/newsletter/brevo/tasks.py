"""Brevo tasks"""

import logging

from django.apps import apps
from django.conf import settings

from joanie.celery_app import app

from . import Brevo

logger = logging.getLogger(__name__)


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
