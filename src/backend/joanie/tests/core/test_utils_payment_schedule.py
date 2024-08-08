"""
Test suite for payment schedule util
"""

import uuid
from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from stockholm import Money

from joanie.core import factories
from joanie.core.enums import (
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
)
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
        If the withdrawal date is after the course start date, the retun date should be the
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
        calculate due dates event with withdrawal date corresponding to the signed contract date
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

    def test_utils_payment_schedule_generate_2_parts_withdrawal_date_higher_than_course_date_date(
        self,
    ):
        """
        Check that order's schedule is correctly set for 1 part
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
        Check that order's schedule is correctly set for 1 part
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
            "due_date": date(2024, 1, 17).isoformat(),
        }

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
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
            "due_date": date(2024, 1, 13).isoformat(),
        }

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
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
            "due_date": date(2024, 1, 17).isoformat(),
        }

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
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

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
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

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.localdate", return_value=mocked_now):
            self.assertEqual(payment_schedule.has_installments_to_debit(order), False)
