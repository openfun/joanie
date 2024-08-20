"""
Test suite for payment schedule tasks
"""

import json
from datetime import date, datetime
from decimal import Decimal as D
from logging import Logger
from unittest import mock
from zoneinfo import ZoneInfo

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from rest_framework.test import APIRequestFactory
from stockholm import Money

from joanie.core.enums import (
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import (
    OrderFactory,
    OrderGeneratorFactory,
    UserAddressFactory,
    UserFactory,
)
from joanie.core.tasks.payment_schedule import (
    debit_pending_installment,
    send_mail_reminder_installment_debit_task,
)
from joanie.payment import get_payment_backend
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseLogMixinTestCase


class PaymentScheduleTasksTestCase(TestCase, BaseLogMixinTestCase):
    """
    Test suite for payment schedule tasks
    """

    maxDiff = None

    @mock.patch.object(
        DummyPaymentBackend,
        "create_zero_click_payment",
        side_effect=DummyPaymentBackend().create_zero_click_payment,
    )
    def test_utils_payment_schedule_debit_pending_installment_succeeded(
        self, mock_create_zero_click_payment
    ):
        """Check today's installment is processed"""
        owner = UserFactory(
            email="john.doe@acme.org",
            first_name="John",
            last_name="Doe",
            language="en-us",
        )
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="6134df5e-a7eb-4cb3-aceb-d0abfe330af6",
            owner=owner,
            state=ORDER_STATE_PENDING,
            main_invoice=InvoiceFactory(),
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

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            debit_pending_installment.run(order.id)

        mock_create_zero_click_payment.assert_called_once_with(
            order=order,
            credit_card_token=order.credit_card.token,
            installment={
                "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                "amount": Money("200.00"),
                "due_date": date(2024, 1, 17),
                "state": PAYMENT_STATE_PENDING,
            },
        )

    def test_utils_payment_schedule_debit_pending_installment_no_card(self):
        """Check today's installment is processed"""
        order = OrderFactory(
            state=ORDER_STATE_PENDING,
            credit_card=None,
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

        mocked_now = datetime(2024, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            debit_pending_installment.run(order.id)

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
        self.assertEqual(order.state, ORDER_STATE_TO_SAVE_PAYMENT_METHOD)

    @mock.patch.object(Logger, "info")
    @mock.patch.object(
        DummyPaymentBackend,
        "handle_notification",
        side_effect=DummyPaymentBackend().handle_notification,
    )
    @mock.patch.object(
        DummyPaymentBackend,
        "create_zero_click_payment",
        side_effect=DummyPaymentBackend().create_zero_click_payment,
    )
    def test_utils_payment_schedule_should_catch_up_late_payments_for_installments_still_unpaid(
        self, mock_create_zero_click_payment, mock_handle_notification, mock_logger
    ):
        """
        When the due date has come, we should verify that there are no missed previous
        installments that were not paid, which still require a payment. In the case where a
        previous installment is found that was not paid, we want our task to handle it and
        trigger the payment with the method `create_zero_click_payment`. We then verify that
        the method `handle_notification` updates the order's payment schedule for the installments
        that were paid.
        """
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
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

        expected_calls = [
            mock.call(
                order=order,
                credit_card_token=order.credit_card.token,
                installment={
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ),
            mock.call(
                order=order,
                credit_card_token=order.credit_card.token,
                installment={
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": PAYMENT_STATE_PENDING,
                },
            ),
        ]

        mocked_now = datetime(2024, 3, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            debit_pending_installment.run(order.id)

        mock_create_zero_click_payment.assert_has_calls(expected_calls, any_order=False)

        backend = get_payment_backend()
        first_request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={
                "id": "pay_1932fbc5-d971-48aa-8fee-6d637c3154a5",
                "type": "payment",
                "state": "success",
            },
            format="json",
        )
        first_request.data = json.loads(first_request.body.decode("utf-8"))
        backend.handle_notification(first_request)

        mock_handle_notification.assert_called_with(first_request)
        mock_logger.assert_called_with(
            "Mail is sent to %s from dummy payment", "john.doe@acme.org"
        )
        mock_logger.reset_mock()

        second_request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={
                "id": "pay_168d7e8c-a1a9-4d70-9667-853bf79e502c",
                "type": "payment",
                "state": "success",
            },
            format="json",
        )
        second_request.data = json.loads(second_request.body.decode("utf-8"))
        backend.handle_notification(second_request)

        mock_handle_notification.assert_called_with(second_request)
        mock_logger.assert_called_with(
            "Mail is sent to %s from dummy payment", "john.doe@acme.org"
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
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
        },
        JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS=2,
        DEFAULT_CURRENCY="EUR",
    )
    def test_payment_scheduled_send_mail_reminder_installment_debit_task_full_cycle(
        self,
    ):
        """
        According to the value configured in the setting `JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS`,
        that is 2 days for this test, the command should find the orders that must be treated
        and calls the method responsible to send the reminder email to the owner orders.
        """
        owner_1 = UserFactory(
            first_name="John",
            last_name="Doe",
            email="john.doe@acme.org",
            language="fr-fr",
        )
        UserAddressFactory(owner=owner_1)
        owner_2 = UserFactory(
            first_name="Sam", last_name="Doe", email="sam@fun-test.fr", language="fr-fr"
        )
        UserAddressFactory(owner=owner_2)
        order_1 = OrderGeneratorFactory(
            owner=owner_1,
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=D("5"),
            product__title="Product 1",
        )
        order_1.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order_1.payment_schedule[0]["due_date"] = date(2024, 1, 17)
        order_1.payment_schedule[1]["id"] = "1932fbc5-d971-48aa-8fee-6d637c3154a5"
        order_1.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order_1.payment_schedule[1]["state"] = PAYMENT_STATE_PENDING
        order_1.save()
        order_2 = OrderGeneratorFactory(
            owner=owner_2,
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=D("5"),
            product__title="Product 2",
        )
        order_2.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order_2.payment_schedule[1]["id"] = "a1cf9f39-594f-4528-a657-a0b9018b90ad"
        order_2.payment_schedule[1]["due_date"] = date(2024, 2, 17)
        order_2.save()
        # This order should be ignored by the django command `send_mail_upcoming_debit`
        order_3 = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT,
            product__price=D("5"),
            product__title="Product 2",
        )
        order_3.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order_3.payment_schedule[1]["due_date"] = date(2024, 2, 18)
        order_3.save()

        # Orders that should be found with their installment that will be debited soon
        expected_calls = [
            mock.call.delay(
                order_id=order_2.id,
                installment_id="a1cf9f39-594f-4528-a657-a0b9018b90ad",
            ),
            mock.call.delay(
                order_id=order_1.id,
                installment_id="1932fbc5-d971-48aa-8fee-6d637c3154a5",
            ),
        ]

        with (
            mock.patch(
                "django.utils.timezone.localdate", return_value=date(2024, 2, 15)
            ),
            mock.patch(
                "joanie.core.tasks.payment_schedule.send_mail_reminder_installment_debit_task"
            ) as mock_send_mail_reminder_installment_debit_task,
        ):
            call_command("send_mail_upcoming_debit")

        mock_send_mail_reminder_installment_debit_task.assert_has_calls(
            expected_calls, any_order=False
        )

        # Trigger now the task `send_mail_reminder_installment_debit_task` for order_1
        send_mail_reminder_installment_debit_task.run(
            order_id=order_1.id, installment_id=order_1.payment_schedule[1]["id"]
        )

        # Check if mail was sent to owner_1 about next upcoming debit
        self.assertEqual(mail.outbox[0].to[0], "john.doe@acme.org")
        self.assertIn("will be debited in 2 days.", mail.outbox[0].subject)
        email_content_1 = " ".join(mail.outbox[0].body.split())
        fullname_1 = order_1.owner.get_full_name()
        self.assertIn(f"Hello {fullname_1}", email_content_1)
        self.assertIn("installment will be withdrawn on 2 days", email_content_1)
        self.assertIn("We will try to debit an amount of", email_content_1)
        self.assertIn("3,5", email_content_1)
        self.assertIn("Product 1", email_content_1)

        # Trigger now the task `send_mail_reminder_installment_debit_task` for order_2
        send_mail_reminder_installment_debit_task.run(
            order_id=order_2.id, installment_id=order_2.payment_schedule[1]["id"]
        )

        # Check if mail was sent to owner_2 about next upcoming debit
        self.assertEqual(mail.outbox[1].to[0], "sam@fun-test.fr")
        self.assertIn("will be debited in 2 days.", mail.outbox[1].subject)
        fullname_2 = order_2.owner.get_full_name()
        email_content_2 = " ".join(mail.outbox[1].body.split())
        self.assertIn(f"Hello {fullname_2}", email_content_2)
        self.assertIn("installment will be withdrawn on 2 days", email_content_2)
        self.assertIn("We will try to debit an amount of", email_content_2)
        self.assertIn("1,5", email_content_2)
        self.assertIn("Product 2", email_content_2)
