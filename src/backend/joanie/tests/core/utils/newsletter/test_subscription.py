"""Test suite for newsletter subscription utilities."""

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from joanie.core.factories import UserFactory
from joanie.core.models import User
from joanie.core.utils.newsletter.subscription import (
    check_commercial_newsletter_subscription_webhook,
    set_commercial_newsletter_subscription,
    synchronize_brevo_subscriptions,
)
from joanie.tests.base import BaseLogMixinTestCase


class UtilsNewsletterSubscriptionTestCase(TestCase, BaseLogMixinTestCase):
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

    @patch("joanie.core.utils.newsletter.subscription.Brevo")
    def test_synchronize_brevo_subscriptions(self, mock_brevo):
        """
        Test synchronize brevo subscriptions
        """
        contacts = [
            {
                "email": f"user_{i}@example.com",
                "listIds": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
            }
            for i in range(5)
        ]
        user_1 = UserFactory(email=contacts[1]["email"])
        user_2 = UserFactory(email=contacts[3]["email"])

        mock_brevo().get_contacts_count.return_value = len(contacts)
        mock_brevo().get_contacts.return_value = contacts

        synchronize_brevo_subscriptions.run()

        user_1.refresh_from_db()
        self.assertTrue(user_1.has_subscribed_to_commercial_newsletter)
        user_2.refresh_from_db()
        self.assertTrue(user_2.has_subscribed_to_commercial_newsletter)
        self.assertEqual(mock_brevo().get_contacts_count.call_count, 1)
        self.assertEqual(mock_brevo().get_contacts.call_count, 1)
        self.assertEqual(mock_brevo().subscribe_to_commercial_list.call_count, 0)

    @patch("joanie.core.utils.newsletter.subscription.Brevo")
    def test_synchronize_brevo_subscriptions_loop(self, mock_brevo):
        """
        Test synchronize brevo subscriptions with multiple loops
        """
        contacts = []
        users = []
        for i in range(1500):
            contacts.append(
                {
                    "email": f"user_{i}@example.com",
                    "listIds": [settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID],
                }
            )
            if i % 2 == 0:
                users.append(
                    UserFactory.build(
                        email=contacts[i]["email"],
                        has_subscribed_to_commercial_newsletter=i % 4 == 0,
                    )
                )

        def contacts_mock(offset, limit, **kwargs):
            return contacts[offset : offset + limit]

        User.objects.bulk_create(users)
        mock_brevo().get_contacts_count.return_value = len(contacts)
        mock_brevo().get_contacts.side_effect = contacts_mock

        with self.assertLogs() as logger:
            synchronize_brevo_subscriptions.run()

        mock_brevo().get_contacts_count.assert_called_once()
        self.assertEqual(mock_brevo().get_contacts.call_count, 3)
        mock_brevo().get_contacts.assert_any_call(limit=500, offset=0)
        mock_brevo().get_contacts.assert_any_call(limit=500, offset=500)
        mock_brevo().get_contacts.assert_any_call(limit=500, offset=1000)
        mock_brevo().subscribe_to_commercial_list.assert_not_called()

        expected = [
            "Total contacts: 1500",
            "Processing contacts from 0 to 500 / 1500",
            "Processing contacts from 500 to 1000 / 1500",
            "Processing contacts from 1000 to 1500 / 1500",
            "Updated 750 users",
        ]
        self.assertLogsContains(logger, expected)
