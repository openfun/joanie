"""Test case for the synchronize_brevo_subscriptions command."""

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from joanie.tests.base import BaseLogMixinTestCase


class SynchronizeBrevoSubscriptionsCommandTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test case for the synchronize_brevo_subscriptions command.
    """

    @patch(
        "joanie.core.management.commands.synchronize_brevo_subscriptions"
        ".synchronize_brevo_subscriptions"
    )
    def test_commands_synchronize_brevo_subscriptions(
        self, mock_synchronize_brevo_subscriptions
    ):
        """
        Test the handle method.
        """
        with self.assertLogs() as logger:
            call_command("synchronize_brevo_subscriptions")

        mock_synchronize_brevo_subscriptions.delay.assert_called_once()
        self.assertLogsContains(logger, "Synchronizing brevo subscriptions")
