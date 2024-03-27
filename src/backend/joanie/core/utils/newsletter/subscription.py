"""Utility methods for newsletter subscription."""

from joanie.celery_app import app
from joanie.core.utils.newsletter.brevo import Brevo


@app.task(bind=True)
def set_commercial_newsletter_subscription(self, user):  # pylint: disable=unused-argument
    """
    Set the newsletter subscription for the user.
    """
    brevo_user = Brevo(user.to_dict())
    if user.has_subscribed_to_commercial_newsletter:
        return brevo_user.subscribe_to_commercial_list()

    return brevo_user.unsubscribe_from_commercial_list()
