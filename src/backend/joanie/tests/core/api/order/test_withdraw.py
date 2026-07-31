"""Tests for the Order withdraw API."""

import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import mail

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OrderWithdrawApiTest(BaseAPITestCase):
    """Test the API of the Order withdraw endpoint."""

    maxDiff = None

    def test_api_order_withdraw_anonymous(self):
        """
        Anonymous user cannot withdraw order
        """
        order = factories.OrderFactory()

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/withdraw/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)
        order.refresh_from_db()
        self.assertNotEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_withdraw_authenticated_unexisting(self):
        """
        User should receive 404 when withdrawing a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/orders/{uuid.uuid4()}/withdraw/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_order_withdraw_authenticated_not_owned(self):
        """
        Authenticated user should not be able to withdraw order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/withdraw/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_withdraw_authenticated_owned(self):
        """
        User should be able to withdraw owned orders as long as first payment
        is not due
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        mocked_now = datetime(2024, 1, 12, 8, 8, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            order = factories.OrderGeneratorFactory(
                owner=user,
                payment_schedule=[
                    {
                        "id": uuid.uuid4(),
                        "amount": "200.00",
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                    {
                        "id": uuid.uuid4(),
                        "amount": "300.00",
                        "due_date": "2024-02-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
                state=enums.ORDER_STATE_PENDING,
            )

            response = self.client.post(
                f"/api/v1.0/orders/{order.id}/withdraw/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertStatusCodeEqual(response, HTTPStatus.OK)
            order.refresh_from_db()
            self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_withdraw_authenticated_owned_error(self):
        """
        User should not be able to withdraw owned orders if first payment is due
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        mocked_now = datetime(2024, 1, 18, 8, 8, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            order = factories.OrderGeneratorFactory(
                owner=user,
                payment_schedule=[
                    {
                        "id": uuid.uuid4(),
                        "amount": "200.00",
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                    {
                        "id": uuid.uuid4(),
                        "amount": "300.00",
                        "due_date": "2024-02-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
                state=enums.ORDER_STATE_PENDING,
            )

            response = self.client.post(
                f"/api/v1.0/orders/{order.id}/withdraw/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertContains(
                response,
                "Cannot withdraw order after the first installment due date",
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
            order.refresh_from_db()
            self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

    def test_api_order_withdraw_authenticated_no_payment_schedule(self):
        """
        User should not be able to withdraw owned orders if there is no payment schedule
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderGeneratorFactory(owner=user, payment_schedule=[])

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/withdraw/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No payment schedule found for this order",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_withdraw_authenticated_product_certificate(self):
        """
        Authenticated user should be able to withdraw an order with product type certificate
        when he has waived the withdrawal right but has not yet reached the withdrawal date limit.
        When the date is beyond the limit, he gets an error in return. When the request is valid,
        the order gets updated in the field `withdrawn_requested_at` and the state passes to
        `pending_withdraw`.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        mocked_now = datetime(2026, 7, 29, 14, tzinfo=ZoneInfo("UTC"))
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            for day in range(15, 20):
                enrollment = factories.EnrollmentFactory(user=user)
                product = factories.ProductFactory(
                    type=enums.PRODUCT_TYPE_CERTIFICATE,
                    contract_definition_order=None,
                    certificate_definition=factories.CertificateDefinitionFactory(),
                    courses=[enrollment.course_run.course],
                    price=10.00,
                )
                for value in [True, False]:
                    with self.subTest(value=value, day=day):
                        order = factories.OrderGeneratorFactory(
                            owner=user,
                            product=product,
                            enrollment=enrollment,
                            course=None,
                            state=enums.ORDER_STATE_COMPLETED,
                            has_waived_withdrawal_right=value,
                        )

                        withdrawal_date_request = mocked_now + timedelta(days=day)
                        with mock.patch(
                            "django.utils.timezone.now",
                            return_value=withdrawal_date_request,
                        ):
                            response = self.client.post(
                                f"/api/v1.0/orders/{order.id}/withdraw/",
                                HTTP_AUTHORIZATION=f"Bearer {token}",
                            )

                            order.refresh_from_db()

                            if day <= settings.JOANIE_WITHDRAWAL_PERIOD_DAYS and value:
                                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                                self.assertEqual(
                                    order.state, enums.ORDER_STATE_PENDING_WITHDRAW
                                )
                                self.assertEqual(
                                    order.withdrawn_requested_at,
                                    withdrawal_date_request,
                                )
                                self.assertIsNone(order.withdrawn_confirmation_at)
                            elif (
                                day <= settings.JOANIE_WITHDRAWAL_PERIOD_DAYS
                                and not value
                            ):
                                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                                self.assertEqual(
                                    order.state, enums.ORDER_STATE_CANCELED
                                )
                                self.assertEqual(
                                    order.withdrawn_requested_at,
                                    withdrawal_date_request,
                                )
                                self.assertEqual(
                                    order.withdrawn_confirmation_at,
                                    withdrawal_date_request,
                                )
                            else:
                                self.assertStatusCodeEqual(
                                    response, HTTPStatus.UNPROCESSABLE_ENTITY
                                )
                                self.assertEqual(
                                    order.state, enums.ORDER_STATE_COMPLETED
                                )
                                self.assertIsNone(order.withdrawn_requested_at)
                                self.assertIsNone(order.withdrawn_confirmation_at)

                            # Cancel the order to continue each cases
                            order.flow.cancel()

    def test_api_order_withdraw_authenticated_product_credential(self):
        """
        Authenticated user should be able to withdraw an order with product credential when
        they have not waived their withdrawal right and the request is made within the date limit.
        If so, the order gets cancelled. Otherwise, if the withdrawal right was taken, it's not
        possible to withdraw the order. When the request is valid, we should find values into
        those fields `withdrawn_requested_at`, `withdrawn_confirmation_at` and the order should
        be cancelled.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        mocked_now = datetime(2026, 7, 29, 14, tzinfo=ZoneInfo("UTC"))
        for day in range(15, 20):
            with self.subTest(day=day):
                course_run = factories.CourseRunFactory(
                    enrollment_start=mocked_now,
                    start=mocked_now + timedelta(days=20),
                    end=mocked_now + timedelta(days=40),
                    course=factories.CourseFactory(),
                )
                offering = factories.OfferingFactory(
                    course=course_run.course,
                    product=factories.ProductFactory(
                        price=10,
                        type=enums.PRODUCT_TYPE_CREDENTIAL,
                        target_courses=[course_run.course],
                        contract_definition_order=factories.ContractDefinitionFactory(),
                    ),
                    organizations=[factories.OrganizationFactory()],
                )
                for value in [True, False]:
                    with self.subTest(value=value, day=day):
                        order = factories.OrderGeneratorFactory(
                            owner=user,
                            product=offering.product,
                            state=enums.ORDER_STATE_SIGNING,
                            has_waived_withdrawal_right=value,
                            payment_schedule=[
                                {
                                    "id": uuid.uuid4(),
                                    "amount": "3.00",
                                    "due_date": "2026-08-15",
                                    "state": enums.PAYMENT_STATE_PENDING,
                                },
                                {
                                    "id": uuid.uuid4(),
                                    "amount": "7.00",
                                    "due_date": "2026-09-15",
                                    "state": enums.PAYMENT_STATE_PENDING,
                                },
                            ],
                        )
                        order.submit_for_signature(user=order.owner)
                        order.contract.student_signed_on = mocked_now
                        order.contract.save()
                        order.flow.update()

                        withdrawal_date_request = mocked_now + timedelta(days=day)
                        with mock.patch(
                            "django.utils.timezone.now",
                            return_value=withdrawal_date_request,
                        ):
                            response = self.client.post(
                                f"/api/v1.0/orders/{order.id}/withdraw/",
                                HTTP_AUTHORIZATION=f"Bearer {token}",
                            )

                            order.refresh_from_db()
                            # breakpoint()
                            if (
                                day <= settings.JOANIE_WITHDRAWAL_PERIOD_DAYS
                                and not value
                            ):
                                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                                self.assertEqual(
                                    order.state, enums.ORDER_STATE_CANCELED
                                )
                                self.assertEqual(
                                    order.withdrawn_requested_at,
                                    withdrawal_date_request,
                                )
                                self.assertEqual(
                                    order.withdrawn_confirmation_at,
                                    withdrawal_date_request,
                                )
                            else:
                                self.assertStatusCodeEqual(
                                    response, HTTPStatus.UNPROCESSABLE_ENTITY
                                )
                                self.assertEqual(
                                    order.state,
                                    enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
                                )
                                self.assertIsNone(order.withdrawn_requested_at)
                                self.assertIsNone(order.withdrawn_confirmation_at)

                            order.flow.cancel()
