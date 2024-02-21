# pylint: disable=protected-access
"""
Test suite for order payment schedule models
"""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from joanie.core import factories
from joanie.tests.base import BaseLogMixinTestCase


class OrderModelsTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test suite for order payment schedule
    """

    maxDiff = None

    def test_models_order_schedule_retraction_date(self):
        """
        Check that the retraction date is a business day
        """
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
        )

        self.assertEqual(
            contract.order._retraction_date(),
            datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
        )

    def test_models_order_schedule_retraction_date_no_contract(self):
        """
        Should raise an error if the order has no contract
        """
        order = factories.OrderFactory()

        with (
            self.assertRaises(ObjectDoesNotExist) as context,
            self.assertLogs("joanie") as logger,
        ):
            order._retraction_date()

        self.assertEqual(str(context.exception), "Order has no contract")
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Contract does not exist, cannot retrieve retraction date",
                    {"order": dict},
                ),
            ],
        )

    def test_models_order_schedule_retraction_date_weekend(self):
        """
        Check that the retraction date is next business day
        """
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 2, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 2, 1, 14, tzinfo=ZoneInfo("UTC")),
        )

        self.assertEqual(
            contract.order._retraction_date(),
            datetime(2024, 2, 19, 0, 0, tzinfo=ZoneInfo("UTC")),
        )

    def test_models_order_schedule_retraction_date_new_year_eve(self):
        """
        Check that the retraction date is next business day after the New Year's Eve
        """
        contract = factories.ContractFactory(
            student_signed_on=datetime(2023, 12, 14, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(
                2023, 12, 14, 14, tzinfo=ZoneInfo("UTC")
            ),
        )

        self.assertEqual(
            contract.order._retraction_date(),
            datetime(2024, 1, 2, 0, 0, tzinfo=ZoneInfo("UTC")),
        )
