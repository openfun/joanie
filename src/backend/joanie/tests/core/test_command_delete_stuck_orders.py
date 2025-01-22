"""Tests for the `delete_stuck_orders` management command."""

from unittest import mock

from django.core.management import call_command

from joanie.tests.base import LoggingTestCase


class DeleteStuckOrdersCommandTestCase(LoggingTestCase):
    """Test case for the management command `delete_stuck_orders`."""

    @mock.patch("joanie.core.utils.order.delete_stuck_orders", return_value=(2, 10))
    def test_commands_delete_stuck_orders(self, mock_delete_stuck_orders):
        """
        This command should call the method `delete_stuck_orders` util and
        log the count of orders deleted.
        """
        expected_logs = [
            ("INFO", "Deleted 2 orders that were stucked in signing states."),
            (
                "INFO",
                "Deleted 10 order that were stucked in to save payment method.",
            ),
        ]

        with self.assertLogs() as logger:
            call_command("delete_stuck_orders")

        self.assertTrue(mock_delete_stuck_orders.assert_called_once_with)
        self.assertLogsEquals(logger.records, expected_logs)
