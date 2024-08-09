"""
Test suite for payment schedule tasks
"""

import json
from datetime import datetime
from logging import Logger
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIRequestFactory

from joanie.core.enums import (
    ORDER_STATE_PENDING,
    ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import OrderFactory, UserAddressFactory, UserFactory
from joanie.core.tasks.payment_schedule import process_today_installment
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
    def test_utils_payment_schedule_process_today_installment_succeeded(
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
            process_today_installment.run(order.id)

        mock_create_zero_click_payment.assert_called_once_with(
            order=order,
            credit_card_token=order.credit_card.token,
            installment={
                "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                "amount": "200.00",
                "due_date": "2024-01-17",
                "state": PAYMENT_STATE_PENDING,
            },
        )

    def test_utils_payment_schedule_process_today_installment_no_card(self):
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
            process_today_installment.run(order.id)

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
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ),
            mock.call(
                order=order,
                credit_card_token=order.credit_card.token,
                installment={
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ),
        ]

        mocked_now = datetime(2024, 3, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            process_today_installment.run(order.id)
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
