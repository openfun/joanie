"""Test suite for newsletter subscription utilities."""

from unittest.mock import patch

from django.test import TestCase

from joanie.core.factories import UserFactory
from joanie.core.utils.newsletter.subscription import (
    check_commercial_newsletter_subscription_webhook,
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

        set_commercial_newsletter_subscription.run(user.to_dict())

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

        set_commercial_newsletter_subscription.run(user.to_dict())

        mock_brevo().unsubscribe_from_commercial_list.assert_called_once()

    @patch("joanie.core.models.accounts.set_commercial_newsletter_subscription")
    @patch("joanie.core.utils.newsletter.subscription.Brevo")
    def test_check_commercial_newsletter_subscription_webhook(
        self, mock_brevo, mock_set_commercial_newsletter_subscription
    ):
        """
        If the contact has unsubscribed from the commercial newsletter list,
        its subscription status will be updated in our database,
        triggering the removal from the list.
        """
        mock_brevo().has_unsubscribed_from_commercial_newsletter.return_value = True
        user = UserFactory(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )
        mock_set_commercial_newsletter_subscription.delay.assert_called_once()
        mock_set_commercial_newsletter_subscription.reset_mock()

        check_commercial_newsletter_subscription_webhook.run([user.email])

        mock_brevo().has_unsubscribed_from_commercial_newsletter.assert_called_once()
        user.refresh_from_db()
        self.assertFalse(user.has_subscribed_to_commercial_newsletter)
        mock_set_commercial_newsletter_subscription.delay.assert_called_once()

    @patch("joanie.core.models.accounts.set_commercial_newsletter_subscription")
    @patch("joanie.core.utils.newsletter.subscription.Brevo")
    def test_check_commercial_newsletter_subscription_webhook_no_user(
        self, mock_brevo, mock_set_commercial_newsletter_subscription
    ):
        """
        If the contact has unsubscribed from the commercial newsletter list,
        its subscription status will be updated in our database,
        triggering the removal from the list.
        """
        mock_brevo().has_unsubscribed_from_commercial_newsletter.return_value = True
        user = UserFactory(
            has_subscribed_to_commercial_newsletter=True,
            email="user@example.com",
        )
        mock_set_commercial_newsletter_subscription.delay.assert_called_once()
        mock_set_commercial_newsletter_subscription.reset_mock()

        check_commercial_newsletter_subscription_webhook.run([user.email])

        mock_brevo().has_unsubscribed_from_commercial_newsletter.assert_called_once()
        user.refresh_from_db()
        self.assertFalse(user.has_subscribed_to_commercial_newsletter)
        mock_set_commercial_newsletter_subscription.delay.assert_called_once()
