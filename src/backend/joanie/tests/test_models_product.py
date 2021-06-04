"""
Test suite for products models
"""
import datetime
import logging
from decimal import Decimal as D

from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from marion.models import DocumentRequest

from joanie.core import enums, factories, models

EXPIRATION_YEAR = (timezone.now() + datetime.timedelta(days=730)).year
CREDIT_CARD_DATA = {
    "name": "Personal",
    "card_number": "1111222233334444",
    "expiration_date": f"01/{EXPIRATION_YEAR}",
    "cryptogram": "222",
}


class ProductModelsTestCase(TestCase):
    """Test suite for the Product model."""

    def test_models_product_price_format(self):
        """The price field should be a decimal with 2 digits (money)."""
        product = factories.ProductFactory(price=23)
        self.assertEqual(product.price, D("23.00"))

    def test_models_product_course_runs_unique(self):
        """A product can only be linked once to a given course run."""
        relation = factories.ProductCourseRelationFactory()
        with self.assertRaises(IntegrityError):
            factories.ProductCourseRelationFactory(
                course=relation.course, product=relation.product
            )

    def test_models_product_course_runs_relation_sorted_by_position(self):
        """The product/course relation should be sorted by position."""
        product = factories.ProductFactory()
        factories.ProductCourseRelationFactory.create_batch(5, product=product)

        expected_courses = list(
            p.course for p in models.ProductCourseRelation.objects.order_by("position")
        )

        ordered_courses = list(product.target_courses.order_by("product_relations"))
        self.assertEqual(ordered_courses, expected_courses)

    @override_settings(JOANIE_VAT=19.6)
    def test_generate_invoice(self):
        """Create an invoice for a product order"""

        address = factories.AddressFactory()
        user = factories.UserFactory()
        user.addresses.add(address)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product, owner=user)

        invoice = order.generate_invoice()
        self.assertEqual(DocumentRequest.objects.count(), 1)
        self.assertEqual(invoice.get_document_path().name, f"{invoice.document_id}.pdf")
        self.assertEqual(
            invoice.context_query["order"]["customer"]["address"],
            address.get_full_address(),
        )
        order.refresh_from_db()
        now = timezone.localtime(timezone.now())
        self.assertTrue(order.invoice_ref.startswith(now.strftime("%Y")))

    def test_model_order_generate_certificate(self):
        """Generate a certificate for a product order"""

        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[course],
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        order = factories.OrderFactory(product=product)

        certificate = order.generate_certificate()
        self.assertEqual(DocumentRequest.objects.count(), 1)
        self.assertEqual(
            certificate.attachment.name,
            f"{DocumentRequest.objects.get().document_id}.pdf",
        )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
    )
    def test_model_order_proceed_to_payment(self):
        """Proceed to pay an order"""

        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[course],
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        order = factories.OrderFactory(product=product, state=enums.ORDER_STATE_PENDING)
        user = order.owner

        # try to pay with credit card data
        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            # pay the order
            order.proceed_to_payment(**CREDIT_CARD_DATA)
            # payment backend log success message
            self.assertTrue("succeeded" in logs.output[0])
            self.assertEqual(len(logs.output), 1)
            order.refresh_from_db()
            # order is now in state PAID
            self.assertEqual(order.state, enums.ORDER_STATE_PAID)

            # try to pay again but nothing happened
            order.proceed_to_payment(**CREDIT_CARD_DATA)
            self.assertEqual(len(logs.output), 1)

            # create a new order and now test payment with credit card registration
            course = factories.CourseFactory()
            product = factories.ProductFactory(
                courses=[course],
                certificate_definition=factories.CertificateDefinitionFactory(),
            )
            order = factories.OrderFactory(
                product=product,
                state=enums.ORDER_STATE_PENDING,
                owner=user,
            )
            CREDIT_CARD_DATA["save"] = True
            order.proceed_to_payment(**CREDIT_CARD_DATA)
            # payment backend log a new success message
            self.assertTrue("succeeded" in logs.output[1])
            self.assertTrue(
                f"Credit card ****{CREDIT_CARD_DATA['card_number'][-4:]} successfully registered"
                in logs.output[2]
            )
            self.assertEqual(len(logs.output), 3)
            order.refresh_from_db()
            # order is now in state PAID
            self.assertEqual(order.state, enums.ORDER_STATE_PAID)
            # a credit card has been saved in db
            credit_card = order.owner.creditcards.get()
            self.assertEqual(
                credit_card.last_numbers, CREDIT_CARD_DATA.get("card_number")[-4:]
            )
            self.assertEqual(
                credit_card.expiration_date, datetime.date(EXPIRATION_YEAR, 1, 31)
            )

            # pay an other order with credit card just registered
            course = factories.CourseFactory()
            product = factories.ProductFactory(
                courses=[course],
                certificate_definition=factories.CertificateDefinitionFactory(),
            )
            order = factories.OrderFactory(
                product=product,
                state=enums.ORDER_STATE_PENDING,
                owner=user,
            )
            order.proceed_to_payment(id=credit_card.uid)
            order.refresh_from_db()
            self.assertEqual(order.state, enums.ORDER_STATE_PAID)
            self.assertTrue("Oneclick payment" in logs.output[3])
            self.assertTrue("succeeded" in logs.output[3])
            self.assertEqual(len(logs.output), 4)
