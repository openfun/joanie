"""
Test suite for payment schedule util
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from stockholm import Money

from joanie.core import factories
from joanie.core.enums import (
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
)
from joanie.core.exceptions import InvalidConversionError
from joanie.core.utils import payment_schedule
from joanie.tests.base import BaseLogMixinTestCase

# pylint: disable=protected-access, too-many-public-methods


@override_settings(
    JOANIE_PAYMENT_SCHEDULE_LIMITS={
        1: (100,),
        5: (30, 70),
        10: (30, 45, 45),
        100: (20, 30, 30, 20),
    },
    DEFAULT_CURRENCY="EUR",
    JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS=2,
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
        signed_contract_date = date(2024, 1, 1)
        course_start_date = date(2024, 3, 1)

        self.assertEqual(
            payment_schedule._withdrawal_limit_date(
                signed_contract_date, course_start_date
            ),
            date(2024, 1, 17),
        )

    def test_utils_payment_schedule_withdrawal_limit_date_weekend(self):
        """
        Check that the withdrawal date is next business day
        """
        signed_contract_date = date(2024, 2, 1)
        course_start_date = date(2024, 3, 1)

        self.assertEqual(
            payment_schedule._withdrawal_limit_date(
                signed_contract_date, course_start_date
            ),
            date(2024, 2, 19),
        )

    def test_utils_payment_schedule_withdrawal_limit_date_new_year_eve(self):
        """
        Check that the withdrawal date is next business day after the New Year's Eve
        """
        signed_contract_date = date(2023, 12, 14)
        course_start_date = date(2024, 3, 1)

        self.assertEqual(
            payment_schedule._withdrawal_limit_date(
                signed_contract_date, course_start_date
            ),
            date(2024, 1, 2),
        )

    def test_utils_payment_schedule_withdrawal_higher_than_course_start_date(self):
        """
        If the withdrawal date is after the course start date, the return date should be the
        signed contract date
        """
        signed_contract_date = date(2024, 1, 1)
        course_start_date = date(2024, 1, 10)

        self.assertEqual(
            payment_schedule._withdrawal_limit_date(
                signed_contract_date, course_start_date
            ),
            date(2024, 1, 1),
        )

    def test_utils_payment_schedule_withdrawal_higher_than_course_start_date_even_weekend(
        self,
    ):
        """
        If the withdrawal date is after the course start date even the weekend,
        the return date should be the signed contract date
        """
        # The contract date is the tuesday 14th dec 2023, as the withdrawal period is
        # set to 16 days, the withdrawal limit date will be the saturday 30th dec 2023.
        signed_contract_date = date(2023, 12, 14)
        course_start_date = date(2023, 11, 21)

        self.assertEqual(
            payment_schedule._withdrawal_limit_date(
                signed_contract_date, course_start_date
            ),
            date(2023, 12, 14),
        )

    def test_utils_payment_schedule_get_installments_percentages(self):
        """
        Check that the correct payment limits are returned for different amounts
        """
        self.assertEqual(payment_schedule._get_installments_percentages(3), (30, 70))
        self.assertEqual(payment_schedule._get_installments_percentages(5), (30, 70))

        self.assertEqual(
            payment_schedule._get_installments_percentages(7), (30, 45, 45)
        )
        self.assertEqual(
            payment_schedule._get_installments_percentages(10), (30, 45, 45)
        )

        self.assertEqual(
            payment_schedule._get_installments_percentages(80), (20, 30, 30, 20)
        )
        self.assertEqual(
            payment_schedule._get_installments_percentages(100), (20, 30, 30, 20)
        )
        self.assertEqual(
            payment_schedule._get_installments_percentages(150), (20, 30, 30, 20)
        )

    def test_utils_payment_schedule_calculate_due_dates_one_percentage_count(self):
        """
        Check that the due dates are correctly calculated when there is only one percentage count
        """
        withdrawal_date = date(2024, 1, 1)
        course_start_date = date(2024, 2, 1)
        course_end_date = date(2024, 3, 20)
        percentages_count = 1

        due_dates = payment_schedule._calculate_due_dates(
            withdrawal_date, course_start_date, course_end_date, percentages_count
        )

        self.assertEqual(
            due_dates,
            [
                date(2024, 1, 1),
            ],
        )

    def test_utils_payment_schedule_calculate_due_dates(self):
        """
        Check that the due dates are correctly calculated
        """
        withdrawal_date = date(2024, 1, 1)
        course_start_date = date(2024, 2, 1)
        course_end_date = date(2024, 3, 20)
        percentages_count = 2

        due_dates = payment_schedule._calculate_due_dates(
            withdrawal_date, course_start_date, course_end_date, percentages_count
        )

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
        withdrawal_date = date(2024, 1, 1)
        course_start_date = date(2024, 2, 1)
        course_end_date = date(2024, 2, 20)
        percentages_count = 3

        due_dates = payment_schedule._calculate_due_dates(
            withdrawal_date, course_start_date, course_end_date, percentages_count
        )

        self.assertEqual(
            due_dates, [withdrawal_date, course_start_date, course_end_date]
        )

    def test_utils_payment_schedule_calculate_due_dates_withdrawal_date_close_to_course_start_date(
        self,
    ):
        """
        Calculate due dates event with withdrawal date corresponding to the signed contract date
        """
        withdrawal_date = date(2024, 1, 1)
        course_start_date = date(2024, 1, 10)
        course_end_date = date(2024, 3, 20)
        percentages_count = 3

        due_dates = payment_schedule._calculate_due_dates(
            withdrawal_date, course_start_date, course_end_date, percentages_count
        )

        self.assertEqual(
            due_dates,
            [
                date(2024, 1, 1),
                date(2024, 1, 10),
                date(2024, 2, 10),
            ],
        )

    def test_utils_payment_schedule_calculate_due_dates_start_date_before_withdrawal(
        self,
    ):
        """
        Check that the due dates are correctly calculated when the course start date is before
        the withdrawal date
        """
        withdrawal_date = date(2024, 1, 1)
        course_start_date = date(2023, 2, 1)
        course_end_date = date(2024, 3, 20)
        percentages_count = 2

        due_dates = payment_schedule._calculate_due_dates(
            withdrawal_date, course_start_date, course_end_date, percentages_count
        )

        self.assertEqual(
            due_dates,
            [
                date(2024, 1, 1),
                date(2024, 2, 1),
            ],
        )

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
        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid]
            installments = payment_schedule._calculate_installments(
                total, due_dates, percentages
            )

        self.assertEqual(
            installments,
            [
                {
                    "id": first_uuid,
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 2, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_2_parts_withdrawal_date_higher_than_course_start_date(
        self,
    ):
        """
        Check that order's schedule is correctly set for 2 part when the withdrawal date is
        higher than the course start date
        """
        total = 3
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 1, 10, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 10),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_1_part(self):
        """
        Check that order's schedule is correctly set for 1 part
        """
        total = 1
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(1.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_2_parts(self):
        """
        Check that order's schedule is correctly set for 2 part
        """
        total = 3
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(0.90, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(2.10, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_3_parts(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        total = 10
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("d727a139-be3b-4b7d-bbae-dacbe90f1c37")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(3.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(4.50, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money(2.50, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 4, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts(self):
        """
        Check that order's schedule is correctly set for 4 parts
        """
        total = 100
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("d727a139-be3b-4b7d-bbae-dacbe90f1c37")
        fourth_uuid = uuid.UUID("8d327896-f397-44f4-953e-996e43ac4040")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid, fourth_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 4, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": fourth_uuid,
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 5, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts_2(self):
        """
        Check that order's schedule is correctly set for 4 parts
        """
        total = 100
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 7, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("d727a139-be3b-4b7d-bbae-dacbe90f1c37")
        fourth_uuid = uuid.UUID("8d327896-f397-44f4-953e-996e43ac4040")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid, fourth_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 4, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": fourth_uuid,
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 5, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts_end_date(self):
        """
        Check that order's schedule is correctly set for an amount that should be
        split in 4 parts, but the end date is before the third part
        """
        total = 100
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 3, 20, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("d727a139-be3b-4b7d-bbae-dacbe90f1c37")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(20.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(30.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money(50.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 20),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_payment_schedule_generate_4_parts_tricky_amount(self):
        """
        Check that order's schedule is correctly set for 3 parts
        """
        total = 999.99
        signed_contract_date = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_start_date = datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC"))
        course_end_date = datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC"))

        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("d727a139-be3b-4b7d-bbae-dacbe90f1c37")
        fourth_uuid = uuid.UUID("8d327896-f397-44f4-953e-996e43ac4040")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid, fourth_uuid]
            schedule = payment_schedule.generate(
                total, signed_contract_date, course_start_date, course_end_date
            )

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money(200.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money(300.0, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money(300.00, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 4, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": fourth_uuid,
                    "amount": Money(199.99, settings.DEFAULT_CURRENCY),
                    "due_date": date(2024, 5, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_utils_is_installment_to_debit_today(self):
        """
        Check that the installment is to debit if the due date is today.
        """
        installment = {
            "state": PAYMENT_STATE_PENDING,
            "due_date": date(2024, 1, 17),
        }

        mocked_now = date(2024, 1, 17)
        with mock.patch("django.utils.timezone.localdate", return_value=mocked_now):
            self.assertEqual(
                payment_schedule.is_installment_to_debit(installment), True
            )

    def test_utils_is_installment_to_debit_past(self):
        """
        Check that the installment is to debit if the due date is reached.
        """
        installment = {
            "state": PAYMENT_STATE_PENDING,
            "due_date": date(2024, 1, 13),
        }

        mocked_now = date(2024, 1, 17)
        with mock.patch("django.utils.timezone.localdate", return_value=mocked_now):
            self.assertEqual(
                payment_schedule.is_installment_to_debit(installment), True
            )

    def test_utils_is_installment_to_debit_paid_today(self):
        """
        Check that the installment is not to debit if the due date is today but its
        state is paid
        """
        installment = {
            "state": PAYMENT_STATE_PAID,
            "due_date": date(2024, 1, 17),
        }

        mocked_now = date(2024, 1, 17)
        with mock.patch("django.utils.timezone.localdate", return_value=mocked_now):
            self.assertEqual(
                payment_schedule.is_installment_to_debit(installment), False
            )

    def test_utils_has_installments_to_debit_true(self):
        """
        Check that the order has installments to debit if at least one is to debit.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2023-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.50",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        order.refresh_from_db()

        mocked_now = date(2024, 1, 17)
        with mock.patch("django.utils.timezone.localdate", return_value=mocked_now):
            self.assertEqual(payment_schedule.has_installments_to_debit(order), True)

    def test_utils_has_installments_to_debit_false(self):
        """
        Check that the order has not installments to debit if no installment are pending
        or due date is not reached.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2023-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.50",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        order.refresh_from_db()

        mocked_now = date(2024, 1, 17)
        with mock.patch("django.utils.timezone.localdate", return_value=mocked_now):
            self.assertEqual(payment_schedule.has_installments_to_debit(order), False)

    def test_utils_payment_schedule_convert_date_str_to_date_object(self):
        """
        Check that the method `convert_date_str_to_date_object` converts an isoformat string
        of a date into a date object
        """
        date_str = "2024-04-26"

        date_object = payment_schedule.convert_date_str_to_date_object(date_str)

        self.assertEqual(date_object, date(2024, 4, 26))

    def test_utils_payment_schedule_convert_date_str_to_date_object_raises_invalid_conversion(
        self,
    ):
        """
        Check that the method `convert_date_str_to_date_object` raises the exception
        `InvalidConversionError` when a string with an incorrect ISO date format is passed as
        the `due_date` value.
        """
        date_str_1 = "abc-04-26"
        date_str_2 = "2024-08-30T14:41:08.504233"

        with self.assertRaises(InvalidConversionError) as context:
            payment_schedule.convert_date_str_to_date_object(date_str_1)

        self.assertEqual(
            str(context.exception),
            "Invalid date format for date_str: Invalid isoformat string: 'abc-04-26'.",
        )

        with self.assertRaises(InvalidConversionError) as context:
            payment_schedule.convert_date_str_to_date_object(date_str_2)

        self.assertEqual(
            str(context.exception),
            "Invalid date format for date_str: Invalid isoformat "
            "string: '2024-08-30T14:41:08.504233'.",
        )

    def test_utils_payment_schedule_convert_amount_str_to_money_object(self):
        """
        Check that the method `convert_amount_str_to_money_object` converts a string value
        representing an amount into a money object.
        """
        item = "22.00"

        amount = payment_schedule.convert_amount_str_to_money_object(item)

        self.assertEqual(amount, Money("22.00"))

    def test_utils_payment_schedule_convert_amount_str_to_money_object_raises_invalid_conversion(
        self,
    ):
        """
        Check that the method `convert_amount_str_to_money_object` raises the exception
        `InvalidConversionError` when a string with an incorrect format for an amount is passed.
        """
        amount_1 = "abc"
        amount_2 = "124,00"

        with self.assertRaises(InvalidConversionError) as context:
            payment_schedule.convert_amount_str_to_money_object(amount_1)

        self.assertEqual(
            str(context.exception),
            "Invalid format for amount: Input value cannot be used as monetary amount : 'abc'.",
        )

        with self.assertRaises(InvalidConversionError) as context:
            payment_schedule.convert_amount_str_to_money_object(amount_2)

        self.assertEqual(
            str(context.exception),
            "Invalid format for amount: Input value cannot be used as monetary amount : '124,00'.",
        )

    def test_utils_is_next_installment_to_debit_in_payment_schedule(self):
        """
        The method `is_next_installment_to_debit` should return a boolean
        whether the installment due date is equal to the passed parameter `due_date`
        value set in the settings named `JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS`.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=D("100"),
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[0]["due_date"] = date(2024, 1, 17)
        order.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order.payment_schedule[2]["due_date"] = date(2024, 3, 17)
        order.payment_schedule[3]["due_date"] = date(2024, 4, 17)
        order.save()

        with mock.patch(
            "django.utils.timezone.localdate", return_value=date(2024, 2, 15)
        ):
            due_date = timezone.localdate() + timedelta(
                days=settings.JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS
            )
        # Should return False for the 1st installment
        self.assertEqual(
            payment_schedule.is_next_installment_to_debit(
                installment=order.payment_schedule[0],
                due_date=due_date,
            ),
            False,
        )
        # Should return True for the 2nd installment
        self.assertEqual(
            payment_schedule.is_next_installment_to_debit(
                installment=order.payment_schedule[1],
                due_date=due_date,
            ),
            True,
        )
        # Should return False for the 3rd installment
        self.assertEqual(
            payment_schedule.is_next_installment_to_debit(
                installment=order.payment_schedule[2],
                due_date=due_date,
            ),
            False,
        )
        # Should return False for the 4th installment
        self.assertEqual(
            payment_schedule.is_next_installment_to_debit(
                installment=order.payment_schedule[3],
                due_date=due_date,
            ),
            False,
        )

    def test_utils_send_mail_reminder_for_installment_debit(self):
        """
        The method `send_mail_reminder_for_installment_debit` should send an email with
        the informations about the upcoming installment. We should find the number of days
        until the debit according to the setting `JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS`,
        which is 2 days for this test.
        """
        order = factories.OrderGeneratorFactory(
            owner=factories.UserFactory(
                first_name="John",
                last_name="Doe",
                email="sam@fun-test.fr",
                language="en-us",
            ),
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=D("100"),
            product__title="Product 1",
        )
        order.payment_schedule[0]["due_date"] = date(2024, 1, 17)
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order.payment_schedule[1]["due_date"] = PAYMENT_STATE_PENDING
        order.save()

        payment_schedule.send_mail_reminder_for_installment_debit(
            order, order.payment_schedule[1]
        )

        self.assertEqual(mail.outbox[0].to[0], "sam@fun-test.fr")
        self.assertIn("will be debited in", mail.outbox[0].subject)

        # Check body
        email_content = " ".join(mail.outbox[0].body.split())
        fullname = order.owner.get_full_name()
        self.assertIn(f"Hello {fullname}", email_content)
        self.assertIn("installment will be withdrawn on 2 days", email_content)
        self.assertIn("We will try to debit an amount of", email_content)
        self.assertIn("30.00", email_content)
        self.assertIn("Product 1", email_content)

    def test_utils_send_mail_reminder_for_installment_debit_in_french_language(self):
        """
        The method `send_mail_reminder_for_installment_debit` should send an email with
        the informations about the upcoming installment in the current language of the user
        when the translation exists in french language.
        """
        owner = factories.UserFactory(
            first_name="John",
            last_name="Doe",
            email="sam@fun-test.fr",
            language="fr-fr",
        )
        product = factories.ProductFactory(price=D("100.00"), title="Product 1")
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = factories.OrderGeneratorFactory(
            product=product,
            owner=owner,
            state=ORDER_STATE_PENDING_PAYMENT,
        )
        order.payment_schedule[0]["due_date"] = date(2024, 1, 17)
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order.payment_schedule[1]["due_date"] = PAYMENT_STATE_PENDING
        order.save()

        payment_schedule.send_mail_reminder_for_installment_debit(
            order, order.payment_schedule[1]
        )

        self.assertEqual(mail.outbox[0].to[0], "sam@fun-test.fr")
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Produit 1", email_content)
        self.assertIn("30,00", email_content)

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
            ("de-de", ("German")),
        )
    )
    def test_utils_send_mail_reminder_for_installment_debit_should_use_fallback_language(
        self,
    ):
        """
        The method `send_mail_reminder_for_installment_debit` should send an email with
        the informations about the upcoming installment in the fallback language if the
        translation does not exist in the current language of the user.
        """
        owner = factories.UserFactory(
            first_name="John",
            last_name="Doe",
            email="sam@fun-test.de",
            language="de-de",
        )
        product = factories.ProductFactory(price=D("100.00"), title="Product 1")
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = factories.OrderGeneratorFactory(
            product=product,
            owner=owner,
            state=ORDER_STATE_PENDING_PAYMENT,
        )
        order.payment_schedule[0]["due_date"] = date(2024, 1, 17)
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order.payment_schedule[1]["due_date"] = PAYMENT_STATE_PENDING
        order.save()

        payment_schedule.send_mail_reminder_for_installment_debit(
            order, order.payment_schedule[1]
        )

        self.assertEqual(mail.outbox[0].to[0], "sam@fun-test.de")
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)
        self.assertIn("30.00", email_content)
