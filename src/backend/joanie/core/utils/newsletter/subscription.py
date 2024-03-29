"""Utility methods for newsletter subscription."""

import logging

from django.apps import apps

from joanie.celery_app import app
from joanie.core.utils.newsletter.brevo import Brevo

logger = logging.getLogger(__name__)


@app.task
def set_commercial_newsletter_subscription(user_dict):
    """
    Set the newsletter subscription for the user.
    """
    brevo_user = Brevo(user_dict)
    if user_dict.get("has_subscribed_to_commercial_newsletter"):
        logger.info(
            "User %s has subscribed to the commercial newsletter", user_dict.get("id")
        )
        return brevo_user.subscribe_to_commercial_list()

    logger.info(
        "User %s has unsubscribed from the commercial newsletter", user_dict.get("id")
    )
    return brevo_user.unsubscribe_from_commercial_list()


@app.task
def check_commercial_newsletter_subscription_webhook(emails):
    """
    Check the commercial newsletter subscription status of a user.

    If the contact has unsubscribed from the commercial newsletter list,
    its subscription status will be updated in our database, triggering the removal from the list.
    """
    User = apps.get_model("core", "User")  # pylint: disable=invalid-name

    for email in emails:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            continue

        brevo_user = Brevo(user.to_dict())
        if brevo_user.has_unsubscribed_from_commercial_newsletter():
            logger.info(
                "User %s has unsubscribed from the commercial newsletter", user.email
            )
            user.has_subscribed_to_commercial_newsletter = False
            user.save()
