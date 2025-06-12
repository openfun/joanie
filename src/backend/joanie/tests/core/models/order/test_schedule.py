# pylint: disable=protected-access, too-many-lines
"""
Test suite for order payment schedule models
"""

import uuid
from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.utils import timezone

from stockholm import Money

from joanie.core import factories
from joanie.core.enums import (
    ORDER_STATE_CANCELED,
    ORDER_STATE_COMPLETED,
    ORDER_STATE_FAILED_PAYMENT,
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_REFUNDING,
    ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUNDED,
    PAYMENT_STATE_REFUSED,
    PRODUCT_TYPE_CERTIFICATE,
    PRODUCT_TYPE_CREDENTIAL,
)
from joanie.core.models import CourseState, Order
from joanie.core.utils import payment_schedule
from joanie.tests.base import ActivityLogMixingTestCase, LoggingTestCase


# pylint: disable=too-many-public-methods
@override_settings(
    JOANIE_PAYMENT_SCHEDULE_LIMITS={
        5: (30, 70),
        10: (30, 35, 35),
        100: (20, 30, 30, 20),
    },
    DEFAULT_CURRENCY="EUR",
)
class OrderModelsTestCase(LoggingTestCase, ActivityLogMixingTestCase):
    """
    Test suite for order payment schedule
    """

    maxDiff = None

    def test_models_order_schedule_get_schedule_dates_with_contract(self):
        """
        Check that the schedule dates are correctly calculated for order with contract
        """
        student_signed_on_date = timezone.now()
        course_run_start_date = timezone.now() + timedelta(days=30 * 2)
        course_run_end_date = timezone.now() + timedelta(days=30 * 5)
        course_run = factories.CourseRunFactory(
            start=course_run_start_date,
            end=course_run_end_date,
        )
        contract = factories.ContractFactory(
            student_signed_on=student_signed_on_date,
            submitted_for_signature_on=student_signed_on_date,
            order__product__target_courses=[course_run.course],
        )

        signed_contract_date, course_start_date, course_end_date = (
            contract.order.get_schedule_dates()
        )

        self.assertEqual(signed_contract_date, student_signed_on_date)
        self.assertEqual(course_start_date, course_run_start_date)
        self.assertEqual(course_end_date, course_run_end_date)

    def test_models_order_schedule_get_schedule_dates_without_contract(self):
        """
        Check that the schedule dates are correctly calculated for order without contract
        """
        course_run_start_date = timezone.now() + timedelta(days=30 * 2)
        course_run_end_date = timezone.now() + timedelta(days=30 * 5)
        course_run = factories.CourseRunFactory(
            start=course_run_start_date,
            end=course_run_end_date,
        )
        order = factories.OrderFactory(
            state=ORDER_STATE_COMPLETED,
            product__target_courses=[course_run.course],
        )

        mocked_now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            signed_contract_date, course_start_date, course_end_date = (
                order.get_schedule_dates()
            )

        self.assertEqual(signed_contract_date, mocked_now)
        self.assertEqual(course_start_date, course_run_start_date)
        self.assertEqual(course_end_date, course_run_end_date)

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
            contract.order.get_schedule_dates()

        self.assertEqual(
            str(context.exception), "['Cannot retrieve start or end date for order']"
        )
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Cannot retrieve start or end date for order",
                    {"order": dict},
                ),
            ],
        )

    def test_models_order_schedule_get_schedule_dates_archived_course_run(self):
        """
        Should ignore archived course run when calculating schedule dates
        """
        archived_run = factories.CourseRunFactory(state=CourseState.ARCHIVED_CLOSED)
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__target_courses=[archived_run.course],
        )

        # As the only available course run is archived,
        # an error should be raised when trying to get the schedule dates
        with (
            self.assertRaises(ValidationError) as context,
            self.assertLogs("joanie") as logger,
        ):
            contract.order.get_schedule_dates()

        self.assertEqual(
            str(context.exception), "['Cannot retrieve start or end date for order']"
        )
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Cannot retrieve start or end date for order",
                    {"order": dict},
                ),
            ],
        )

    def test_models_order_schedule_2_parts(self):
        """
        Check that order's schedule is correctly set for 2 parts
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price=3,
            order__product__target_courses=[course_run.course],
        )
        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        mocked_now = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        with (
            mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock,
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            uuid4_mock.side_effect = [first_uuid, second_uuid]
            schedule = contract.order.generate_schedule()

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

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "id": str(first_uuid),
                    "amount": Money("0.90"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": str(second_uuid),
                    "amount": Money("2.10"),
                    "due_date": date(2024, 3, 1),
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
            start=datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price=6,
            order__product__target_courses=[course_run.course],
        )
        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        mocked_now = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        with (
            mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock,
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid]
            schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money("1.80"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money("2.10"),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money("2.10"),
                    "due_date": date(2024, 4, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "id": str(first_uuid),
                    "amount": Money("1.80"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": str(second_uuid),
                    "amount": Money("2.10"),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": str(third_uuid),
                    "amount": Money("2.10"),
                    "due_date": date(2024, 4, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_3_parts_session_already_started(self):
        """
        Check that order's schedule is correctly set for 3 parts
        when the session has already started
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2023, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2023, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        contract = factories.ContractFactory(
            student_signed_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            order__product__price=6,
            order__product__target_courses=[course_run.course],
        )
        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        third_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        mocked_now = datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC"))
        with (
            mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock,
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            uuid4_mock.side_effect = [first_uuid, second_uuid, third_uuid]
            schedule = contract.order.generate_schedule()

        self.assertEqual(
            schedule,
            [
                {
                    "id": first_uuid,
                    "amount": Money("1.80"),
                    "due_date": date(2024, 1, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": second_uuid,
                    "amount": Money("2.10"),
                    "due_date": date(2024, 2, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": third_uuid,
                    "amount": Money("2.10"),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        contract.order.refresh_from_db()
        self.assertEqual(
            contract.order.payment_schedule,
            [
                {
                    "id": str(first_uuid),
                    "amount": Money("1.80"),
                    "due_date": date(2024, 1, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": str(second_uuid),
                    "amount": Money("2.10"),
                    "due_date": date(2024, 2, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": str(third_uuid),
                    "amount": Money("2.10"),
                    "due_date": date(2024, 3, 1),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    def test_models_order_schedule_find_installment(self):
        """Check that matching orders are found"""
        order = factories.OrderFactory(
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ]
        )
        factories.OrderFactory(
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-18",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-18",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-03-18",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-18",
                    "state": PAYMENT_STATE_PENDING,
                },
            ]
        )

        found_orders = Order.objects.find_installments(due_date=date(2024, 2, 17))
        self.assertEqual(len(found_orders), 1)
        self.assertIn(order, found_orders)

    def test_models_order_schedule_find_pending_installments(self):
        """Check that matching orders are found"""
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        order_2 = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        order_3 = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "300.00",
                    "due_date": "2024-03-18",
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "amount": "199.99",
                    "due_date": "2024-04-18",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "300.00",
                    "due_date": "2024-03-18",
                    "state": PAYMENT_STATE_PAID,
                },
            ],
        )

        factories.OrderFactory(
            state=ORDER_STATE_NO_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-18",
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "amount": "200.00",
                    "due_date": "2024-01-18",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        found_orders = Order.objects.find_pending_installments()

        self.assertEqual(len(found_orders), 3)
        self.assertIn(order, found_orders)
        self.assertIn(order_2, found_orders)
        self.assertIn(order_3, found_orders)

    def test_models_order_schedule_set_installment_state(self):
        """Check that the state of an installment can be set."""
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order._set_installment_state(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
            state=PAYMENT_STATE_PAID,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order._set_installment_state(
            installment_id="9fcff723-7be4-4b77-87c6-2865e000f879",
            state=PAYMENT_STATE_REFUSED,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_REFUSED,
                },
            ],
        )

        with self.assertRaises(ValueError):
            order._set_installment_state(
                installment_id="eb402e70-53da-4d67-81a9-b50dd04f571b",
                state=PAYMENT_STATE_REFUSED,
            )

    def test_models_order_schedule_set_installment_paid(self):
        """
        Check that the state of an installment can be set to paid.
        If the paid installment is not the last one, the order state
        should be set to pending payment.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_paid(
            installment_id="1932fbc5-d971-48aa-8fee-6d637c3154a5",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_PENDING_PAYMENT)
        self.assertPaymentSuccessActivityLog(order)

    def test_models_order_schedule_set_installment_paid_first(self):
        """
        Check that the state of an installment can be set to paid.
        If the first installment is paid, the order state should be
        set to pending payment.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_paid(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_PENDING_PAYMENT)
        self.assertPaymentSuccessActivityLog(order)

    def test_models_order_schedule_set_installment_paid_last(self):
        """
        Check that the state of an installment can be set to paid.
        If the last installment is paid, the order state should be
        set to completed.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_paid(
            installment_id="9fcff723-7be4-4b77-87c6-2865e000f879",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PAID,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)
        self.assertPaymentSuccessActivityLog(order)

    def test_models_order_schedule_set_installment_paid_unique(self):
        """
        Check that the state of an installment can be set to paid.
        If there is only one installment, the order state should be
        set to completed.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_paid(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)
        self.assertPaymentSuccessActivityLog(order)

    def test_models_order_schedule_set_installment_refused(self):
        """
        Check that the state of an installment can be set to refused.
        If the refused installment is not the last one, the order state
        should be set to failed payment.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_refused(
            installment_id="1932fbc5-d971-48aa-8fee-6d637c3154a5"
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_FAILED_PAYMENT)
        self.assertPaymentFailedActivityLog(order)

    def test_models_order_schedule_set_installment_refused_first(self):
        """
        Check that the state of an installment can be set to refused.
        If the refused installment is the first one, the order state
        should be set to no payment.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_refused(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_NO_PAYMENT)
        self.assertPaymentFailedActivityLog(order)

    def test_models_order_schedule_set_installment_refused_last(self):
        """
        Check that the state of an installment can be set to refused.
        If the refused installment is the last one, the order state
        should be set to failed payment.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_refused(
            installment_id="9fcff723-7be4-4b77-87c6-2865e000f879",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_REFUSED,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_FAILED_PAYMENT)
        self.assertPaymentFailedActivityLog(order)

    def test_models_order_schedule_set_installment_refused_unique(self):
        """
        Check that the state of an installment can be set to refused.
        If there is only one installment, the order state should be
        set to no payment.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        order.set_installment_refused(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": PAYMENT_STATE_REFUSED,
                },
            ],
        )
        self.assertEqual(order.state, ORDER_STATE_NO_PAYMENT)
        self.assertPaymentFailedActivityLog(order)

    def test_models_order_schedule_withdraw(self):
        """Check that the order can be withdrawn"""
        order = factories.OrderFactory(
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ]
        )
        order.refresh_from_db()

        mocked_now = datetime(2024, 1, 12, 8, 8, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            order.withdraw()

        order.refresh_from_db()
        self.assertEqual(order.state, "canceled")

    def test_models_order_schedule_withdraw_no_schedule(self):
        """If no payment schedule is found, withdraw should raise an error"""
        order = factories.OrderFactory()

        with self.assertRaisesMessage(
            ValidationError, "No payment schedule found for this order"
        ):
            order.withdraw()

    def test_models_order_schedule_withdraw_passed_due_date(self):
        """If the due date has passed, withdraw should raise an error"""
        order = factories.OrderFactory(
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ]
        )
        order.refresh_from_db()

        mocked_now = datetime(2024, 2, 18, 8, 8)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            with self.assertRaisesMessage(
                ValidationError,
                "Cannot withdraw order after the first installment due date",
            ):
                order.withdraw()

    def test_models_order_schedule_get_first_installment_refused_returns_installment_object(
        self,
    ):
        """
        The method `get_first_installment_refused` should return the first installment found
        that is in state `PAYMENT_STATE_REFUSED` in the payment schedule of an order.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        # Prepare data of the 'refused' state installment
        order.payment_schedule[1]["id"] = "1932fbc5-d971-48aa-8fee-6d637c3154a5"
        order.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order.payment_schedule[1]["state"] = PAYMENT_STATE_REFUSED
        # Set the rest of installments to 'pending' state
        order.payment_schedule[2]["state"] = PAYMENT_STATE_PENDING
        order.payment_schedule[3]["state"] = PAYMENT_STATE_PENDING

        installment = order.get_first_installment_refused()

        self.assertDictEqual(
            installment,
            {
                "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                "amount": Money("30.00"),
                "due_date": date(2024, 2, 17),
                "state": PAYMENT_STATE_REFUSED,
            },
        )

    def test_models_order_schedule_get_first_installment_refused_returns_none(self):
        """
        The method `get_first_installment_refused` should return `None` if there is no installment
        in payment schedule found for the order with the state `PAYMENT_STATE_REFUSED`.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[2]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[3]["state"] = PAYMENT_STATE_PENDING

        installment = order.get_first_installment_refused()

        self.assertIsNone(installment)

    def test_models_order_schedule_get_date_next_installment_to_pay(self):
        """
        Should return the date of the next installment to pay for the user on his order's
        payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[2]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[3]["due_date"] = date(2024, 4, 17)

        date_next_installment = order.get_date_next_installment_to_pay()

        self.assertEqual(date_next_installment, date(2024, 4, 17))

    def test_models_order_get_date_next_installment_to_pay_returns_none_if_no_pending_state(
        self,
    ):
        """
        The method `get_date_next_installment_to_pay` should return None if there is no
        `pending` state into the order's payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=5,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_REFUSED

        result = order.get_date_next_installment_to_pay()

        self.assertIsNone(result)

    def test_models_order_schedule_get_remaining_balance_to_pay(self):
        """
        Should return the leftover amount still remaining to be paid on an order's
        payment schedule
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID

        remains = order.get_remaining_balance_to_pay()

        self.assertEqual(remains, Money("50.00"))

    def test_models_order_schedule_get_index_of_last_installment_with_paid_state(self):
        """
        Test that the method `get_installment_index` correctly returns the index of the
        last installment with the state 'paid' in the payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID

        self.assertEqual(
            0,
            order.get_installment_index(state=PAYMENT_STATE_PAID),
        )

        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID

        self.assertEqual(
            1,
            order.get_installment_index(state=PAYMENT_STATE_PAID),
        )

        order.payment_schedule[2]["state"] = PAYMENT_STATE_PAID

        self.assertEqual(
            2,
            order.get_installment_index(state=PAYMENT_STATE_PAID),
        )

    def test_models_order_schedule_get_index_of_last_installment_state_refused(self):
        """
        Test that the method `get_installment_index` correctly returns the index of the
        last installment with the state 'refused' in the payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_REFUSED

        self.assertEqual(
            1,
            order.get_installment_index(state=PAYMENT_STATE_REFUSED),
        )

    def test_models_order_schedule_get_index_of_installment_pending_state_first_occurence(
        self,
    ):
        """
        Test that the method `get_installment_index` correctly returns the index of the
        first installment with the state 'pending' in the payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID

        self.assertEqual(
            2,
            order.get_installment_index(state=PAYMENT_STATE_PENDING, find_first=True),
        )

    def test_models_order_schedule_get_index_of_installment_pending_state_last_occurence(
        self,
    ):
        """
        The method `get_installment_index` should return the last occurence in the
        payment schedule depending the value set of
        `find_first` parameter and also the `state` of the installment payment.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=10,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID

        self.assertEqual(order.get_installment_index(PAYMENT_STATE_PENDING), 2)

    def test_models_order_get_index_of_installment_should_return_none_because_no_refused_state(
        self,
    ):
        """
        The method `get_installment_index` should return None if there is no 'refused' payment
        state present in the payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=5,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID

        self.assertIsNone(order.get_installment_index(PAYMENT_STATE_REFUSED))

    def test_models_order_get_index_of_installment_should_return_none_because_no_paid_state(
        self,
    ):
        """
        The method `get_installment_index` should return None if there is no 'paid' payment
        state present in the payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=5,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PENDING
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PENDING

        self.assertIsNone(order.get_installment_index(PAYMENT_STATE_PAID))

    def test_models_order_get_index_of_installment_should_return_none_because_no_pending_state(
        self,
    ):
        """
        The method `get_installment_index` should return None if there is no 'pending' payment
        state present in the payment schedule.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=5,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_REFUSED

        self.assertIsNone(order.get_installment_index(PAYMENT_STATE_PENDING))

    def test_models_order_set_installment_state_refunded(self):
        """
        Check that the state of an installment can be set to refunded only
        if the installment was in state `paid` and the order's state is 'refunding',
        else it raises an error.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_CANCELED,
            product__price=10,
        )
        # First installment is paid
        order.payment_schedule[0]["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[0]["due_date"] = date(2024, 2, 17)
        # Second installment is pending for payment
        order.payment_schedule[1]["id"] = "1932fbc5-d971-48aa-8fee-6d637c3154a5"
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PENDING
        order.payment_schedule[1]["due_date"] = date(2024, 3, 17)
        # Third installment is pending for payment
        order.payment_schedule[2]["id"] = "168d7e8c-a1a9-4d70-9667-853bf79e502c"
        order.payment_schedule[2]["state"] = PAYMENT_STATE_PENDING
        order.payment_schedule[2]["due_date"] = date(2024, 4, 17)

        order.flow.refunding()

        order.set_installment_refunded(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
        )

        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_REFUNDING)
        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": Money("3.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_REFUNDED,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("3.50"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("3.50"),
                    "due_date": date(2024, 4, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        # Attempt to refund an installment that is still in `pending_payment` state
        # should raise a Value Error
        with self.assertRaises(ValueError) as context:
            order.set_installment_refunded(
                installment_id="1932fbc5-d971-48aa-8fee-6d637c3154a5",
            )

        self.assertEqual(
            str(context.exception),
            "Installment with id 1932fbc5-d971-48aa-8fee-6d637c3154a5 cannot be refund",
        )

        # Passing a fake installment id should raise a ValueError
        with self.assertRaises(ValueError) as context:
            order.set_installment_refunded(
                installment_id="fake_installment_id",
            )

        self.assertEqual(
            str(context.exception),
            "Installment with id fake_installment_id cannot be refund",
        )

    def test_models_order_get_amount_installments_refunded_should_be_zero(self):
        """
        Should return the total amount to was refunded from the payment schedule of an order.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )

        amount_refunded = order.get_amount_installments_refunded()

        self.assertEqual(amount_refunded, Money("0.00"))

    def test_models_order_get_amount_installments_refunded(self):
        """
        Should return the total amount to was refunded from the payment schedule of an order.
        """
        order = factories.OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=100,
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_REFUNDED
        order.payment_schedule[1]["state"] = PAYMENT_STATE_REFUNDED

        amount_refunded = order.get_amount_installments_refunded()

        self.assertEqual(amount_refunded, Money("50.00"))

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            200: (30, 70),
            500: (30, 35, 35),
            1000: (20, 30, 30, 20),
        },
    )
    def test_models_order_payment_schedule_product_type_credential(self):
        """
        When the product is type credential, when the product's price is set between 1 and 200,
        there should always be at least 2 installments.
        """
        prices = ["1.00", "50.00", "100.00", "200.00"]

        for price in prices:
            # Orders with credentials product should always have at minimum 2 installments to pay
            credential_product = factories.ProductFactory(
                price=price,
                type=PRODUCT_TYPE_CREDENTIAL,
            )
            order_credential = factories.OrderGeneratorFactory(
                product=credential_product,
                state=ORDER_STATE_PENDING_PAYMENT,
            )

            self.assertEqual(len(order_credential.payment_schedule), 2)

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            200: (30, 70),
            1000: (20, 30, 30, 20),
        },
    )
    def test_models_order_payment_schedule_product_type_certificate(self):
        """
        When the product is type certificate, no matter the price set, it should always be
        1 installment to pay. We should never have more.
        """
        prices = ["1.00", "199.00", "499.00", "999.00"]
        for price in prices:
            course = factories.CourseFactory()
            product = factories.ProductFactory(
                courses=[course], type=PRODUCT_TYPE_CERTIFICATE, price=price
            )
            enrollment = factories.EnrollmentFactory(
                course_run__course=course,
                course_run__is_listed=True,
                course_run__state=CourseState.FUTURE_OPEN,
                is_active=True,
            )
            order = factories.OrderFactory(
                course=None,
                product=product,
                enrollment=enrollment,
                state=ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            )

            self.assertEqual(order.payment_schedule, [])
            # Generate payment schedule is triggered in order flow post transition success
            order.flow.update()

            self.assertEqual(order.state, ORDER_STATE_PENDING)
            self.assertNotEqual(order.payment_schedule, [])
            self.assertEqual(len(order.payment_schedule), 1)
            self.assertEqual(
                order.payment_schedule[0],
                {
                    "id": order.payment_schedule[0]["id"],
                    "due_date": order.payment_schedule[0]["due_date"],
                    "amount": order.total,
                    "state": PAYMENT_STATE_PENDING,
                },
            )
