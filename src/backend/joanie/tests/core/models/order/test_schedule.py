# pylint: disable=protected-access
"""
Test suite for order payment schedule models
"""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.test import TestCase
from django.test.utils import override_settings

from joanie.core import factories
from joanie.tests.base import BaseLogMixinTestCase


@override_settings(
    PAYMENT_SCHEDULE_LIMITS={5: (30, 70), 10: (30, 45, 45), 100: (20, 30, 30, 20)},
)
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

    def test_models_order_schedule_get_installments_percentages(self):
        """
        Check that the correct payment limits are returned for different amounts
        """
        order = factories.OrderFactory(product__price=3)
        self.assertEqual(order._get_installments_percentages(), (30, 70))
        order = factories.OrderFactory(product__price=5)
        self.assertEqual(order._get_installments_percentages(), (30, 70))

        order = factories.OrderFactory(product__price=7)
        self.assertEqual(order._get_installments_percentages(), (30, 45, 45))
        order = factories.OrderFactory(product__price=10)
        self.assertEqual(order._get_installments_percentages(), (30, 45, 45))

        order = factories.OrderFactory(product__price=80)
        self.assertEqual(order._get_installments_percentages(), (20, 30, 30, 20))
        order = factories.OrderFactory(product__price=100)
        self.assertEqual(order._get_installments_percentages(), (20, 30, 30, 20))
        order = factories.OrderFactory(product__price=150)
        self.assertEqual(order._get_installments_percentages(), (20, 30, 30, 20))

    def test_models_order_schedule_get_schedule_dates(self):
        """
        Check that the schedule dates are correctly calculated
        """
        student_signed_on_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_run_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 8, tzinfo=ZoneInfo("UTC")),
            end=course_run_end_date,
        )
        contract = factories.ContractFactory(
            student_signed_on=student_signed_on_date,
            submitted_for_signature_on=student_signed_on_date,
            order__product__target_courses=[course_run.course],
        )

        start_date, end_date = contract.order._get_schedule_dates()

        self.assertEqual(
            start_date, datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        )
        self.assertEqual(end_date, course_run_end_date)

    def test_models_order_schedule_get_schedule_dates_no_course_run(self):
        """
        Should raise an error if the order has no course run
        """
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
        )

        with (
            self.assertRaises(ValidationError) as context,
            self.assertLogs("joanie") as logger,
        ):
            contract.order._get_schedule_dates()

        self.assertEqual(
            str(context.exception), "['Cannot retrieve end date for order']"
        )
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Cannot retrieve end date for order",
                    {"order": dict},
                ),
            ],
        )

    def test_models_order_schedule_calculate_due_dates(self):
        """
        Check that the due dates are correctly calculated
        """
        start_date = datetime(2024, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 3, 20, 8, tzinfo=ZoneInfo("UTC"))

        with patch(
            "joanie.core.models.products.Order._get_schedule_dates"
        ) as mock_get_schedule_dates:
            mock_get_schedule_dates.return_value = start_date, end_date
            order = factories.OrderFactory(product__price=3)
            due_dates = order._calculate_due_dates(2)

        self.assertEqual(
            due_dates,
            [
                datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
                datetime(2024, 2, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
            ],
        )

    def test_models_order_schedule_calculate_due_dates_end_date(self):
        """
        Check that the due dates are correctly calculated
        when the end date is before the second part.
        No further due date should be calculated.
        """
        start_date = datetime(2024, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 1, 20, 8, tzinfo=ZoneInfo("UTC"))

        with patch(
            "joanie.core.models.products.Order._get_schedule_dates"
        ) as mock_get_schedule_dates:
            mock_get_schedule_dates.return_value = start_date, end_date
            order = factories.OrderFactory(product__price=3)
            due_dates = order._calculate_due_dates(3)

        self.assertEqual(due_dates, [start_date, end_date])
