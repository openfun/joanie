"""Tests for the Order withdraw API."""

import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import mail
from django.test import override_settings

from joanie.core import enums, factories
from joanie.core.models import OrderTargetCourseRelation
from joanie.tests.base import BaseAPITestCase


@override_settings(JOANIE_WITHDRAWAL_PERIOD_DAYS=16)
class OrderWithdrawApiTest(BaseAPITestCase):
    """Test the API of the Order withdraw endpoint."""

    maxDiff = None

    def setUp(self):
        super().setUp()
        self.creation_date = datetime(2026, 6, 25, 14, tzinfo=ZoneInfo("UTC"))

    def _create_order_credential(self, user, has_waived_withdrawal_right):
        """Create an order signed by the student, created at `creation_date`."""
        with mock.patch("django.utils.timezone.now", return_value=self.creation_date):
            course = factories.CourseFactory()
            factories.CourseRunFactory(
                course=course,
                enrollment_start=self.creation_date,
                start=datetime(2026, 8, 27, 14, tzinfo=ZoneInfo("UTC")),
                end=datetime(2026, 10, 1, 14, tzinfo=ZoneInfo("UTC")),
            )
            product = factories.ProductFactory(
                target_courses=[course],
                contract_definition_order=factories.ContractDefinitionFactory(),
            )
            order = factories.OrderGeneratorFactory(
                owner=user,
                product=product,
                state=enums.ORDER_STATE_SIGNING,
                has_waived_withdrawal_right=has_waived_withdrawal_right,
            )
            if not OrderTargetCourseRelation.objects.filter(
                course=course, order=order
            ).exists():
                factories.OrderTargetCourseRelationFactory(
                    course=course, order=order, position=1
                )
            order.submit_for_signature(user=user)
            order.contract.student_signed_on = self.creation_date + timedelta(days=1)
            order.contract.save()
            order.flow.update()
        return order

    def _limit_for(self, order):
        """Withdrawal limit computed with the same clock as the fixture."""
        with mock.patch("django.utils.timezone.now", return_value=self.creation_date):
            return order._withdrawal_limit()  # pylint:disable=protected-access

    def _first_refused_day(self, order):
        """First day offset (from creation_date) at which withdrawal is refused."""
        limit = self._limit_for(order)
        self.assertIsNotNone(limit)
        # `limit >= now` is still eligible, so the first refused day is one past it
        return (limit - self.creation_date).days + 1

    def _withdraw(self, order, token, day):
        """Call the withdraw endpoint `day` days after the order creation."""
        request_date = self.creation_date + timedelta(days=day)
        with mock.patch("django.utils.timezone.now", return_value=request_date):
            response = self.client.post(
                f"/api/v1.0/orders/{order.id}/withdraw/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        order.refresh_from_db()
        return response, request_date

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
        User should not be able to withdraw owned orders unless the contract is signed,
        the payment schedule is not generated and the state is in `to_save_payment_method`.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        for state in [
            enums.ORDER_STATE_DRAFT,
            enums.ORDER_STATE_ASSIGNED,
            enums.ORDER_STATE_TO_OWN,
        ]:
            with self.subTest(state=state):
                order = factories.OrderGeneratorFactory(
                    owner=user,
                    payment_schedule=[],
                    state=state,
                )

                response = self.client.post(
                    f"/api/v1.0/orders/{order.id}/withdraw/",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                self.assertContains(
                    response,
                    "The order's state does not allow withdrawal",
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

    def test_api_order_withdraw_within_period(self):
        """Right not waived + inside the period: the order is cancelled."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for day in range(1, settings.JOANIE_WITHDRAWAL_PERIOD_DAYS + 1):
            with self.subTest(day=day):
                order = self._create_order_credential(
                    user, has_waived_withdrawal_right=False
                )

                response, request_date = self._withdraw(order, token, day)

                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
                self.assertEqual(order.withdrawn_requested_at, request_date)
                self.assertEqual(order.withdrawn_confirmation_at, request_date)

    def test_api_order_withdraw_after_period(self):
        """Right not waived + outside the period: withdrawal is refused."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        probe = self._create_order_credential(user, has_waived_withdrawal_right=False)
        first_refused_day = self._first_refused_day(probe)

        for day in range(first_refused_day, first_refused_day + 5):
            with self.subTest(day=day):
                order = self._create_order_credential(
                    user, has_waived_withdrawal_right=False
                )

                response, _ = self._withdraw(order, token, day)
                order.refresh_from_db()

                self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)
                self.assertNotEqual(order.state, enums.ORDER_STATE_CANCELED)
                self.assertIsNone(order.withdrawn_requested_at)
                self.assertIsNone(order.withdrawn_confirmation_at)

    def test_api_order_withdraw_right_waived(self):
        """Right waived: withdrawal is refused whatever the day."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for day in (1, 15, 16, 17, 18):
            with self.subTest(day=day):
                order = self._create_order_credential(
                    user, has_waived_withdrawal_right=True
                )

                response, _ = self._withdraw(order, token, day)

                self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)
                self.assertEqual(order.state, enums.ORDER_STATE_TO_SAVE_PAYMENT_METHOD)
                self.assertIsNone(order.withdrawn_requested_at)
                self.assertIsNone(order.withdrawn_confirmation_at)

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
                                # Check email confirming cancelled order
                                self.assertEqual(
                                    "Withdrawal request received",
                                    mail.outbox[0].subject,
                                )
                                self.assertEqual(
                                    mail.outbox[0].to[0], order.owner.email
                                )
                                email_content = " ".join(mail.outbox[0].body.split())
                                self.assertIn(
                                    "will review your request",
                                    email_content,
                                )

                                self.assertEqual(
                                    "Withdrawal request received",
                                    mail.outbox[1].subject,
                                )
                                self.assertEqual(
                                    mail.outbox[1].to[0],
                                    settings.JOANIE_EMAIL_SUPPORT_CERTIFICATE,
                                )
                                email_content = " ".join(mail.outbox[1].body.split())
                                self.assertIn(
                                    "needs your review to validate",
                                    email_content,
                                )
                                mail.outbox.clear()
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
                                # Check email confirming cancelled order
                                self.assertEqual(
                                    "Withdrawal confirmed", mail.outbox[0].subject
                                )
                                self.assertEqual(
                                    mail.outbox[0].to[0], order.owner.email
                                )
                                email_content = " ".join(mail.outbox[0].body.split())
                                self.assertIn(
                                    "has been cancelled accordingly",
                                    email_content,
                                )

                                self.assertEqual(
                                    "Withdrawal confirmed", mail.outbox[1].subject
                                )
                                self.assertEqual(
                                    mail.outbox[1].to[0],
                                    settings.JOANIE_EMAIL_SUPPORT_CERTIFICATE,
                                )
                                email_content = " ".join(mail.outbox[1].body.split())
                                self.assertIn(
                                    "has been confirmed",
                                    email_content,
                                )
                                mail.outbox.clear()
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
