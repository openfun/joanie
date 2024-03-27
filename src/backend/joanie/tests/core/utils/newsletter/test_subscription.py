"""Test suite for newsletter subscription utilities."""

from unittest.mock import patch

from django.test import TestCase

from joanie.core.factories import UserFactory
from joanie.core.utils.newsletter.subscription import (
    set_commercial_newsletter_subscription,
)


class UtilsNewsletterSubscriptionTestCase(TestCase):
    """
    Test suite for newsletter subscription utilities.
    """

    @patch("joanie.core.utils.newsletter.subscription.Brevo")
    def test_set_commercial_newsletter_subscription_true(self, mock_brevo):
        """
        If the user has subscribed to the commercial newsletter, it should be added
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )

        set_commercial_newsletter_subscription(user)

        mock_brevo().subscribe_to_commercial_list.assert_called_once()

    @patch("joanie.core.utils.newsletter.subscription.Brevo")
    def test_set_commercial_newsletter_subscription_false(self, mock_brevo):
        """
        If the user has not subscribed to the commercial newsletter, it should be removed
        """
        user = UserFactory.build(
            has_subscribed_to_commercial_newsletter=False,
            email="user@example.com",
        )

        set_commercial_newsletter_subscription(user)

        mock_brevo().unsubscribe_from_commercial_list.assert_called_once()
