"""Tests for the `cancel_batch_orders` management command."""

from unittest import mock

from django.core.management import call_command

from joanie.tests.base import LoggingTestCase


class CancelBatchOrdersCommandTestCase(LoggingTestCase):
    """Test case for the management command `cancel_batch_orders`."""

    @mock.patch("joanie.core.utils.batch_order.cancel_batch_orders", return_value=3)
    def test_commands_cancel_batch_orders(self, mock_cancel_batch_orders):
        """
        This command should call the method `cancel_batch_orders` util and
        log the count of batch orders are canceled.
        """
        expected_logs = [
            (
                "INFO",
                "Canceled 3 batch orders that was stucked in failed payment states.",
            ),
        ]

        with self.assertLogs() as logger:
            call_command("cancel_batch_orders")

        self.assertTrue(mock_cancel_batch_orders.assert_called_once_with)
        self.assertLogsEquals(logger.records, expected_logs)
