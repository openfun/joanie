"""Tests for the `cleanup_credit_cards` management command."""

from unittest import mock

from django.core.management import call_command

from joanie.tests.base import LoggingTestCase


class CleanupCreditCardsCommandTestCase(LoggingTestCase):
    """Test case for the management command `cleanup_credit_cards`."""

    @mock.patch("joanie.payment.models.CreditCardManager.delete_unused")
    def test_commands_cleanup_credit_cards(self, mock_cleanup_credit_card):
        """
        This command should call the method `cleanup_credit_card` util and
        log the count of orders deleted.
        """
        mock_cleanup_credit_card.return_value = (
            [
                {"order_id": "order_id_1", "card_id": "card_id_1"},
                {"order_id": "order_id_2", "card_id": "card_id_2"},
            ],
            [
                {"card_id": "card_id_1"},
                {"card_id": "card_id_2"},
                {"card_id": "card_id_3"},
            ],
        )

        with self.assertLogs() as logger:
            call_command("cleanup_credit_cards")

        expected_logs = [
            ("INFO", "Unlinked 2 credit cards:"),
            ("INFO", "  order_id_1"),
            ("INFO", "  order_id_2"),
            ("INFO", "Deleted 3 credit cards:"),
            ("INFO", "  card_id_1"),
            ("INFO", "  card_id_2"),
            ("INFO", "  card_id_3"),
        ]
        mock_cleanup_credit_card.assert_called_once()
        self.assertLogsEquals(logger.records, expected_logs)
