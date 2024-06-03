# pylint: disable=protected-access, too-many-lines
"""
Test suite for order payment schedule models
"""

import uuid
from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.test import TestCase
from django.test.utils import override_settings

from stockholm import Money

from joanie.core import factories
from joanie.core.enums import (
    ORDER_STATE_COMPLETED,
    ORDER_STATE_FAILED_PAYMENT,
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.models import Order
from joanie.core.utils import payment_schedule
from joanie.tests.base import ActivityLogMixingTestCase, BaseLogMixinTestCase


@override_settings(
    JOANIE_PAYMENT_SCHEDULE_LIMITS={
        5: (30, 70),
        10: (30, 45, 45),
        100: (20, 30, 30, 20),
    },
    DEFAULT_CURRENCY="EUR",
)
class OrderModelsTestCase(TestCase, BaseLogMixinTestCase, ActivityLogMixingTestCase):
    """
    Test suite for order payment schedule
    """

    maxDiff = None

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

        self.assertEqual(start_date, student_signed_on_date)
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

    def test_models_order_schedule_get_schedule_dates_no_contract(self):
        """
        Should raise an error if the order has no course run
        """
        order = factories.OrderFactory()

        with (
            self.assertRaises(ObjectDoesNotExist) as context,
            self.assertLogs("joanie") as logger,
        ):
            order._get_schedule_dates()

        self.assertEqual(str(context.exception), "Order has no contract")
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Contract does not exist, cannot retrieve withdrawal date",
                    {"order": dict},
                ),
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
        first_uuid = uuid.UUID("1932fbc5-d971-48aa-8fee-6d637c3154a5")
        second_uuid = uuid.UUID("a1cf9f39-594f-4528-a657-a0b9018b90ad")
        with mock.patch.object(payment_schedule.uuid, "uuid4") as uuid4_mock:
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
                    "due_date": date(2024, 2, 17),
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
                    "amount": "0.90",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": str(second_uuid),
                    "amount": "2.10",
                    "due_date": "2024-02-17",
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

    def test_models_order_schedule_find_today_installments(self):
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
        factories.OrderFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-18",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-18",
                    "state": PAYMENT_STATE_REFUSED,
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
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "amount": "199.99",
                    "due_date": "2024-04-18",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        mocked_now = datetime(2024, 2, 17, 1, 10, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            found_orders = Order.objects.find_today_installments()

        self.assertEqual(len(found_orders), 2)
        self.assertIn(order, found_orders)
        self.assertIn(order_2, found_orders)

    def test_models_order_schedule_set_installment_state(self):
        """Check that the state of an installment can be set."""
        order = factories.OrderFactory(
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

        is_first, is_last = order._set_installment_state(
            installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a",
            state=PAYMENT_STATE_PAID,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
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
        self.assertTrue(is_first)
        self.assertFalse(is_last)

        is_first, is_last = order._set_installment_state(
            installment_id="9fcff723-7be4-4b77-87c6-2865e000f879",
            state=PAYMENT_STATE_REFUSED,
        )

        order.refresh_from_db()
        self.assertEqual(
            order.payment_schedule,
            [
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
                    "state": PAYMENT_STATE_REFUSED,
                },
            ],
        )
        self.assertFalse(is_first)
        self.assertTrue(is_last)

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
                    "amount": "200.00",
                    "due_date": "2024-01-17",
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
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_REFUSED,
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
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_REFUSED,
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
                    "amount": "200.00",
                    "due_date": "2024-01-17",
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

        mocked_now = datetime(2024, 2, 18, 8, 8)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            with self.assertRaisesMessage(
                ValidationError,
                "Cannot withdraw order after the first installment due date",
            ):
                order.withdraw()

    def test_models_order_get_first_installment_refused_returns_installment_object(
        self,
    ):
        """
        The method `get_first_installment_refused` should return the first installment found
        that is in state `PAYMENT_STATE_REFUSED` in the payment schedule of an order.
        """
        order = factories.OrderFactory(
            state=ORDER_STATE_FAILED_PAYMENT,
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
                    "state": PAYMENT_STATE_REFUSED,
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

        installment = order.get_first_installment_refused()

        self.assertDictEqual(
            installment,
            {
                "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                "amount": "300.00",
                "due_date": "2024-02-17",
                "state": PAYMENT_STATE_REFUSED,
            },
        )

    def test_models_order_get_first_installment_refused_returns_none(self):
        """
        The method `get_first_installment_refused` should return `None` if there is no installment
        in payment schedule found for the order with the state `PAYMENT_STATE_REFUSED`.
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

        installment = order.get_first_installment_refused()

        self.assertIsNone(installment)
