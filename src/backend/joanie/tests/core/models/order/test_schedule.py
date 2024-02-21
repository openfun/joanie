# pylint: disable=protected-access
"""
Test suite for order payment schedule models
"""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.test import TestCase
from django.test.utils import override_settings

from stockholm import Money

from joanie.core import factories
from joanie.core.enums import (
    PAYMENT_STATE_PAYED,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.tests.base import BaseLogMixinTestCase


@override_settings(
    PAYMENT_SCHEDULE_LIMITS={5: (30, 70), 10: (30, 45, 45), 100: (20, 30, 30, 20)},
    DEFAULT_CURRENCY="EUR",
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

    def test_models_order_schedule_calculate_installments(self):
        """
        Check that the installments are correctly calculated
        """
        order = factories.OrderFactory(product__price=3)
        due_dates = [
            datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
            datetime(2024, 2, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
        ]
        percentages = (30, 70)
        installments = order._calculate_installments(due_dates, percentages)

        self.assertEqual(
            installments,
            [
                {
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 2, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_2_parts(self):
        """
        Check that order's schedule is correctly set for 1 part
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price=3,
            order__product__target_courses=[course_run.course],
        )

        schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 2, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "amount": "0.90",
                    "due_date": "2024-01-17T00:00:00Z",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "2.10",
                    "due_date": "2024-02-17T00:00:00Z",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_3_parts(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price=10,
            order__product__target_courses=[course_run.course],
        )

        schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(3.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(4.50, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 2, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(2.50, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 3, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "amount": "3.00",
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "4.50",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "2.50",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_4_parts(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price=100,
            order__product__target_courses=[course_run.course],
        )

        schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 2, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 3, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 4, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "amount": "20.00",
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "30.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "30.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "20.00",
                    "due_date": "2024-04-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_4_parts_end_date(self):
        """
        Check that order's schedule is correctly set for an amount that should be
        split in 3 parts, but the end date is before the second part
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 1, 20, 8, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 0, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 0, tzinfo=ZoneInfo("UTC")),
            order__product__price=100,
            order__product__target_courses=[course_run.course],
        )

        schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 1, 17, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(80.00, settings.DEFAULT_CURRENCY),
                    "due_date": course_run.end,
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "amount": "20.00",
                    "due_date": datetime(
                        2024, 1, 17, 0, tzinfo=ZoneInfo("UTC")
                    ).isoformat(),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "80.00",
                    "due_date": course_run.end.isoformat(),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_4_parts_tricky_amount(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price="999.99",
            order__product__target_courses=[course_run.course],
        )

        schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(200.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(300.0, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 2, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(300.00, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 3, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(199.99, settings.DEFAULT_CURRENCY),
                    "due_date": datetime(2024, 4, 17, 0, 0, tzinfo=ZoneInfo("UTC")),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17T00:00:00+00:00",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
