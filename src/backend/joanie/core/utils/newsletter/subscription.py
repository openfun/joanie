"""Utility methods for newsletter subscription."""

from joanie.core.utils.newsletter.brevo import Brevo


def set_commercial_newsletter_subscription(user):
    """
    Set the newsletter subscription for the user.
    """
    brevo_user = Brevo(user)
    if user.has_subscribed_to_commercial_newsletter:
        return brevo_user.subscribe_to_commercial_list()

    return brevo_user.unsubscribe_from_commercial_list()
