"""
Test suite for payment schedule util
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from stockholm import Money

from joanie.core.enums import PAYMENT_STATE_PENDING
from joanie.core.utils.payment_schedule import (
    _calculate_due_dates,
    _calculate_installments,
    _get_installments_percentages,
    _withdrawal_limit_date,
    generate,
)
from joanie.tests.base import BaseLogMixinTestCase


@override_settings(
    PAYMENT_SCHEDULE_LIMITS={5: (30, 70), 10: (30, 45, 45), 100: (20, 30, 30, 20)},
    DEFAULT_CURRENCY="EUR",
)
class PaymentScheduleUtilsTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test suite for payment schedule util
    """

    maxDiff = None

    def test_utils_payment_schedule_withdrawal_limit_date(self):
        """
        Check that the withdrawal date is a business day
        """
        start_date = date(2024, 1, 1)

        self.assertEqual(
            _withdrawal_limit_date(start_date),
            date(2024, 1, 17),
        )

    def test_utils_payment_schedule_withdrawal_limit_date_weekend(self):
        """
        Check that the withdrawal date is next business day
        """
        start_date = date(2024, 2, 1)

        self.assertEqual(
            _withdrawal_limit_date(start_date),
            date(2024, 2, 19),
        )

    def test_utils_payment_schedule_withdrawal_limit_date_new_year_eve(self):
        """
        Check that the withdrawal date is next business day after the New Year's Eve
        """
        start_date = date(2023, 12, 14)

        self.assertEqual(
            _withdrawal_limit_date(start_date),
            date(2024, 1, 2),
        )

    def test_utils_payment_schedule_get_installments_percentages(self):
        """
        Check that the correct payment limits are returned for different amounts
        """
        self.assertEqual(_get_installments_percentages(3), (30, 70))
        self.assertEqual(_get_installments_percentages(5), (30, 70))

        self.assertEqual(_get_installments_percentages(7), (30, 45, 45))
        self.assertEqual(_get_installments_percentages(10), (30, 45, 45))

        self.assertEqual(_get_installments_percentages(80), (20, 30, 30, 20))
        self.assertEqual(_get_installments_percentages(100), (20, 30, 30, 20))
        self.assertEqual(_get_installments_percentages(150), (20, 30, 30, 20))

    def test_utils_payment_schedule_calculate_due_dates(self):
        """
        Check that the due dates are correctly calculated
        """
        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 20)
        percentages_count = 2

        due_dates = _calculate_due_dates(start_date, end_date, percentages_count)

        self.assertEqual(
            due_dates,
            [
                date(2024, 1, 1),
                date(2024, 2, 1),
            ],
        )

    def test_utils_payment_schedule_calculate_due_dates_end_date(self):
        """
        Check that the due dates are correctly calculated
        when the end date is before the second part.
        No further due date should be calculated.
        """
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 20)
        percentages_count = 3

        due_dates = _calculate_due_dates(start_date, end_date, percentages_count)

        self.assertEqual(due_dates, [start_date, end_date])

    def test_utils_payment_schedule_calculate_installments(self):
        """
        Check that the installments are correctly calculated
        """
        total = 3
        due_dates = [
            date(2024, 1, 1),
            date(2024, 2, 1),
        ]
        percentages = (30, 70)
        installments = _calculate_installments(total, due_dates, percentages)

        self.assertEqual(
            installments,
            [
                {
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 2, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_2_parts(self):
        """
        Check that order's schedule is correctly set for 1 part
        """
        total = 3
        start_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        schedule = generate(total, start_date, end_date)

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_3_parts(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        total = 10
        start_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        schedule = generate(total, start_date, end_date)

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(3.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(4.50, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(2.50, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts(self):
        """
        Check that order's schedule is correctly set for 4 parts
        """
        total = 100
        start_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        schedule = generate(total, start_date, end_date)

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts_end_date(self):
        """
        Check that order's schedule is correctly set for an amount that should be
        split in 4 parts, but the end date is before the second part
        """
        total = 100
        start_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 1, 20, 8, tzinfo=ZoneInfo("UTC"))

        schedule = generate(total, start_date, end_date)

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(80.00, settings.DEFAULT_CURRENCY),
                    "due_date": end_date.date(),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts_tricky_amount(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        total = 999.99
        start_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        schedule = generate(total, start_date, end_date)

        self.assertEqual(
            schedule,
            [
                {
                    "amount": Money(200.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(300.0, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(300.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": Money(199.99, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
