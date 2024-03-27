"""Utility methods for newsletter subscription."""

from joanie.core.utils.newsletter.brevo import Brevo


def set_commercial_newsletter_subscription(user):
    """
    Set the newsletter subscription for the user.
    """
    if user.has_subscribed_to_commercial_newsletter:
        return Brevo().add_contact_to_commercial_list(user)

    return Brevo().remove_contact_from_commercial_list(user)
