"""Test suite for `prepare_context_data` email utility for installment payments"""

from decimal import Decimal

from django.test import TestCase, override_settings

from stockholm import Money

from joanie.core.enums import (
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import OrderFactory, ProductFactory, UserFactory
from joanie.core.utils.emails import prepare_context_data


@override_settings(
    JOANIE_CATALOG_NAME="Test Catalog",
    JOANIE_CATALOG_BASE_URL="https://richie.education",
)
class UtilsEmailPrepareContextDataInstallmentPaymentTestCase(TestCase):
    """
    Test suite for `prepare_context_data` for email utility when installment is paid or refused
    """

    def test_utils_emails_prepare_context_data_when_installment_debit_is_successful(
        self,
    ):
        """
        When an installment is successfully paid, the `prepare_context_data` method should
        create the context with the following keys : `fullname`, `email`, `product_title`,
        `installment_amount`, `product_price`, `credit_card_last_numbers`,
        `order_payment_schedule`, `dashboard_order_link`, `site`, `remaining_balance_to_pay`,
        `date_next_installment_to_pay`, and `targeted_installment_index`.
        """
        product = ProductFactory(price=Decimal("1000.00"), title="Product 1")
        order = OrderFactory(
            product=product,
            state=ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(
                first_name="John",
                last_name="Doe",
                language="en-us",
                email="johndoe@fun-test.fr",
            ),
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

        context_data = prepare_context_data(
            order, Money("300.00"), product.title, payment_refused=False
        )

        self.assertDictEqual(
            context_data,
            {
                "fullname": "John Doe",
                "email": "johndoe@fun-test.fr",
                "product_title": "Product 1",
                "installment_amount": Money("300.00"),
                "product_price": Money("1000.00"),
                "credit_card_last_numbers": order.credit_card.last_numbers,
                "order_payment_schedule": order.payment_schedule,
                "dashboard_order_link": (
                    f"http://localhost:8070/dashboard/courses/orders/{order.id}/"
                ),
                "site": {
                    "name": "Test Catalog",
                    "url": "https://richie.education",
                },
                "remaining_balance_to_pay": Money("499.99"),
                "date_next_installment_to_pay": "2024-03-17",
                "targeted_installment_index": 1,
            },
        )

    def test_utils_emails_prepare_context_data_when_installment_debit_is_refused(self):
        """
        When an installment debit has been refused, the `prepare_context_data` method should
        create the context and we should not find the following keys : `remaining_balance_to_pay`,
        and `date_next_installment_to_pay`.
        """
        product = ProductFactory(price=Decimal("1000.00"), title="Product 1")
        order = OrderFactory(
            product=product,
            state=ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(
                first_name="John",
                last_name="Doe",
                language="en-us",
                email="johndoe@fun-test.fr",
            ),
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
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        context_data = prepare_context_data(
            order, Money("300.00"), product.title, payment_refused=True
        )

        self.assertNotIn("remaining_balance_to_pay", context_data)
        self.assertNotIn("date_next_installment_to_pay", context_data)
        self.assertDictEqual(
            context_data,
            {
                "fullname": "John Doe",
                "email": "johndoe@fun-test.fr",
                "product_title": "Product 1",
                "installment_amount": Money("300.00"),
                "product_price": Money("1000.00"),
                "credit_card_last_numbers": order.credit_card.last_numbers,
                "order_payment_schedule": order.payment_schedule,
                "dashboard_order_link": (
                    f"http://localhost:8070/dashboard/courses/orders/{order.id}/"
                ),
                "site": {
                    "name": "Test Catalog",
                    "url": "https://richie.education",
                },
                "targeted_installment_index": 2,
            },
        )
