"""Test suite for the management command `synchronize_offerings`."""

from unittest import mock

from django.core.management import call_command

from joanie.core.management.commands import synchronize_offerings
from joanie.tests.base import LoggingTestCase


class SynchronizeOfferingsTestCase(LoggingTestCase):
    """Test case for the management command `synchronize_offerings`."""

    @mock.patch.object(synchronize_offerings, "synchronize_offerings")
    def test_commands_synchronize_offerings(self, mock_synchronize):
        """
        Test that the command calls the synchronize_offerings function.
        """

        with self.assertLogs() as logger:
            call_command("synchronize_offerings")

        mock_synchronize.delay.assert_called_once()
        self.assertLogsContains(logger, "Synchronizing offerings")
