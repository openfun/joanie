"""Test suite for `prepare_context_data` email utility for installment payments"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings

from stockholm import Money

from joanie.core.enums import (
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import OrderGeneratorFactory, ProductFactory, UserFactory
from joanie.core.utils.emails import (
    prepare_context_data,
    prepare_context_for_upcoming_installment,
)


@override_settings(
    JOANIE_CATALOG_NAME="Test Catalog",
    JOANIE_CATALOG_BASE_URL="https://richie.education",
    JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS=2,
    JOANIE_PAYMENT_SCHEDULE_LIMITS={
        1000: (20, 30, 30, 20),
    },
    DEFAULT_CURRENCY="EUR",
)
class UtilsEmailPrepareContextDataInstallmentPaymentTestCase(TestCase):
    """
    Test suite for `prepare_context_data` for email utility when installment is paid or refused
    """

    maxDiff = None

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
        order = OrderGeneratorFactory(
            product=product,
            state=ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(
                first_name="John",
                last_name="Doe",
                language="en-us",
                email="johndoe@fun-test.fr",
            ),
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[2]["due_date"] = date(2024, 3, 17)
        order.save()

        context_data = prepare_context_data(
            order,
            order.payment_schedule[2]["amount"],
            product.title,
            payment_refused=False,
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
                "remaining_balance_to_pay": Money("500.00"),
                "date_next_installment_to_pay": date(2024, 3, 17),
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
        order = OrderGeneratorFactory(
            product=product,
            state=ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(
                first_name="John",
                last_name="Doe",
                language="en-us",
                email="johndoe@fun-test.fr",
            ),
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[2]["state"] = PAYMENT_STATE_REFUSED
        order.payment_schedule[2]["due_date"] = date(2024, 3, 17)
        order.save()

        context_data = prepare_context_data(
            order,
            order.payment_schedule[2]["amount"],
            product.title,
            payment_refused=True,
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

    def test_utils_emails_prepare_context_for_upcoming_installment_email(
        self,
    ):
        """
        When an installment will soon be debited for the order's owners, the method
        `prepare_context_for_upcoming_installment` will prepare the context variable that
        will be used for the email.

        We should find the following keys : `fullname`, `email`, `product_title`,
        `installment_amount`, `product_price`, `credit_card_last_numbers`,
        `order_payment_schedule`, `dashboard_order_link`, `site`, `remaining_balance_to_pay`,
        `date_next_installment_to_pay`, `targeted_installment_index`, and `days_until_debit`
        """
        product = ProductFactory(price=Decimal("1000.00"), title="Product 1")
        order = OrderGeneratorFactory(
            product=product,
            state=ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(
                first_name="John",
                last_name="Doe",
                language="en-us",
                email="johndoe@fun-test.fr",
            ),
        )
        order.payment_schedule[0]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[1]["state"] = PAYMENT_STATE_PAID
        order.payment_schedule[2]["due_date"] = date(2024, 3, 17)
        order.save()

        context_data_for_upcoming_installment_email = (
            prepare_context_for_upcoming_installment(
                order,
                order.payment_schedule[2]["amount"],
                product.title,
                days_until_debit=settings.JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS,
            )
        )

        self.assertDictEqual(
            context_data_for_upcoming_installment_email,
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
                "remaining_balance_to_pay": Money("500.00"),
                "date_next_installment_to_pay": date(2024, 3, 17),
                "targeted_installment_index": 2,
                "days_until_debit": 2,
            },
        )
