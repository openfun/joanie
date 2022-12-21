"""Test suite for the Invoice model."""
import re
from decimal import Decimal as D
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from djmoney.money import Money
from parler.utils.context import switch_language
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core.factories import OrderFactory, ProductFactory
from joanie.payment.factories import InvoiceFactory, TransactionFactory
from joanie.payment.models import Invoice


class InvoiceModelTestCase(TestCase):
    """
    Test case for the Invoice model
    """

    def test_models_invoice_type_invoice(self):
        """
        If invoice has a positive amount, its type should be `invoice` and its
        string representation should be prefixed by "Invoice".
        """
        invoice = InvoiceFactory(order=OrderFactory(), total=100)

        self.assertEqual(invoice.type, "invoice")
        self.assertEqual(str(invoice), f"Invoice {invoice.reference}")

    def test_models_invoice_type_credit_note(self):
        """
        If invoice has a negative amount, its type should be `credit_note`
        """
        invoice = InvoiceFactory(order=OrderFactory(), total=100)
        credit_note = InvoiceFactory(order=invoice.order, parent=invoice, total=-100)

        self.assertEqual(credit_note.type, "credit_note")
        self.assertEqual(str(credit_note), f"Credit note {credit_note.reference}")

    def test_models_invoice_credit_note_with_amount_greater_than_related_invoice_amount(
        self,
    ):
        """
        If a credit note has an amount greater than its parent invoiced balance,
        a ValidationError should be raised.
        """
        # Create an order and its related invoice for 100.00 €
        order = OrderFactory(product=ProductFactory(price=100))
        invoice = InvoiceFactory(order=order, total=order.total)
        # Then link an invoice for 20.00 €
        InvoiceFactory(order=invoice.order, parent=invoice, total=D(20.00))
        # Finally, link a credit note for -10.00 €
        InvoiceFactory(order=invoice.order, parent=invoice, total=D(-10.00))

        # Invoiced balance should be 110.00 €
        self.assertEqual(invoice.invoiced_balance.amount, D(110.00))

        # Credit a credit note greater than invoiced balance should be forbidden
        with self.assertRaises(ValidationError) as context:
            InvoiceFactory(order=order, parent=invoice, total=-111)

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['Credit note amount cannot be greater than its "
                "related invoice invoiced balance.']}"
            ),
        )

    def test_models_invoice_normalize_reference(self):
        """
        When an invoice object is created, its reference should be normalized.
        """
        order = OrderFactory()
        invoice = InvoiceFactory(reference="1", order=order, total=order.total)

        # Reference should have been normalized using current timestamp and
        # order uid (e.g: f04bca42-1639062573511)
        self.assertIsNotNone(re.fullmatch(r"^[0-9a-f]{8}-\d{13}$", invoice.reference))

    def test_models_invoice_protected(self):
        """
        Order deletion should be blocked as long as related invoice exists.
        """
        order = OrderFactory()
        invoice = InvoiceFactory(order=order, total=order.total)

        with self.assertRaises(ProtectedError):
            invoice.order.delete()

    def test_models_invoice_balance(self):
        """
        Invoice.balance should return the current balance
        of the invoice.
        """
        product = ProductFactory(price=500)
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)

        # - At beginning, balance should be -500.00
        self.assertEqual(invoice.balance.amount, D("-500.00"))

        # - Then we received a payment to pay the full order,
        #   balance should be -500.00 + 500.00 = 0.00
        TransactionFactory(total=product.price, invoice=invoice)
        invoice.refresh_from_db()
        self.assertEqual(invoice.balance.amount, D("0.00"))

        # - Then we create a credit note to refund a part of the order (100.00)
        credit_note = InvoiceFactory(order=invoice.order, parent=invoice, total=-100)
        invoice.refresh_from_db()
        self.assertEqual(invoice.balance.amount, D("100.00"))

        # - Then we register the transaction to refund the client (100.00)
        TransactionFactory(
            total=Money(-100.00, order.total.currency),
            invoice=credit_note,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.balance.amount, D("0.00"))

    def test_models_invoice_state_paid(self):
        """
        If invoice balance is greater or equal than zero, transactions_balance
        and invoiced_balance are not equal to zero, invoice state should be paid
        """
        product = ProductFactory(price="100.00")
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)
        TransactionFactory.create_batch(2, total=product.price / 2, invoice=invoice)

        with self.assertNumQueries(7):
            self.assertEqual(invoice.invoiced_balance, order.total)
            self.assertEqual(invoice.transactions_balance, order.total)
            self.assertEqual(invoice.balance.amount, D("0.00"))
            self.assertEqual(invoice.state, "paid")

    def test_models_invoice_state_refunded(self):
        """
        If invoice balance is greater or equal than zero, transactions_balance
        and invoiced_balance are equal to zero,
        invoice state should be refunded
        """
        product = ProductFactory(price="100.00")
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)
        TransactionFactory.create_batch(2, total=product.price / 2, invoice=invoice)

        # - Fully refund the order
        InvoiceFactory(order=invoice.order, parent=invoice, total=-order.total)
        TransactionFactory(invoice=invoice, total=-product.price)

        with self.assertNumQueries(12):
            self.assertEqual(invoice.invoiced_balance.amount, D("0.00"))
            self.assertEqual(invoice.transactions_balance.amount, D("0.00"))
            self.assertEqual(invoice.balance.amount, D("0.00"))
            self.assertEqual(invoice.state, "refunded")

    def test_models_invoice_state_unpaid(self):
        """
        If invoice balance is less than zero,
        invoice state should be unpaid.
        """
        product = ProductFactory(price="100.00")
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)
        TransactionFactory(total=product.price / 2, invoice=invoice)

        with self.assertNumQueries(4):
            self.assertEqual(invoice.balance.amount, D("-50.00"))
            self.assertEqual(invoice.state, "unpaid")

    def test_models_invoice_child_cannot_relies_on_another_child(self):
        """
        An invoice cannot have a parent which is
        a child of another invoice.
        """
        order = OrderFactory()
        parent = InvoiceFactory(order=order, total=order.total)
        child = InvoiceFactory(order=parent.order, parent=parent, total=-order.total)

        with self.assertRaises(ValidationError) as context:
            InvoiceFactory(order=child.order, parent=child, total=20.00)

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['invoice cannot have as parent "
                "another invoice which is a child.']}"
            ),
        )

    def test_models_invoice_relying_on_order_with_a_negative_amount(self):
        """
        An invoice without parent must have a positive total amount otherwise
        a validation error should be raised on save.
        """
        order = OrderFactory()

        with self.assertRaises(ValidationError) as context:
            InvoiceFactory(order=order, total=-200.00)

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Credit note must have a parent invoice.']}",
        )

    def test_models_invoice_without_parent_unique_per_order(self):
        """
        An order can have only one invoice without parent
        """
        order = OrderFactory()

        InvoiceFactory(order=order, total=200.00)

        with self.assertRaises(IntegrityError) as context:
            InvoiceFactory(order=order, total=100.00)

        self.assertRegex(
            str(context.exception),
            (
                "^duplicate key value violates unique constraint "
                '"only_one_invoice_without_parent_per_order"'
            ),
        )

    def test_models_invoice_update_invoice_relying_on_order_with_a_negative_amount(
        self,
    ):
        """
        An invoice without a parent must have a positive total amount otherwise
        an integrity error should be raised when clean is bypassed.
        """
        order = OrderFactory()
        invoice = InvoiceFactory(order=order, total=200.00)

        with self.assertRaises(IntegrityError) as context:
            Invoice.objects.filter(pk=invoice.pk).update(total=-200.00)

        self.assertRegex(
            str(context.exception),
            (
                '"joanie_invoice" violates check constraint '
                '"main_invoice_should_have_a_positive_amount"'
            ),
        )

    def test_models_invoice_localized_context(self):
        """
        When an invoice is created, localized contexts in each enabled
        languages should be created.
        """
        order = OrderFactory()
        invoice = InvoiceFactory(order=OrderFactory(), total=order.total)
        languages = settings.LANGUAGES
        self.assertEqual(len(list(invoice.localized_context)), len(languages))

    def test_models_invoice_get_document_context(self):
        """
        We should get the document context in the provided language. If the translation
        does not exist, we should gracefully fallback to the default language defined
        through parler settings ("en-us" in our case).
        """
        product = ProductFactory(title="Product 1", description="Product 1 description")
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
            description="Description du produit 1",
        )
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)

        context = invoice.get_document_context("en-us")
        self.assertEqual(context["order"]["product"]["name"], "Product 1")
        self.assertEqual(
            context["order"]["product"]["description"], "Product 1 description"
        )

        context = invoice.get_document_context("fr-fr")
        self.assertEqual(context["order"]["product"]["name"], "Produit 1")
        self.assertEqual(
            context["order"]["product"]["description"], "Description du produit 1"
        )

        # When translation for the given language does not exist,
        # we should get the fallback language translation.
        context = invoice.get_document_context("de-de")
        self.assertEqual(context["order"]["product"]["name"], "Product 1")
        self.assertEqual(
            context["order"]["product"]["description"], "Product 1 description"
        )

    def test_models_invoice_document(self):
        """
        Invoice document property which should generate a document
        into the active language
        """
        product = ProductFactory(title="Product 1", description="Product 1 description")
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
            description="Description du produit 1",
        )

        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(invoice.document)).replace("\n", "")
        self.assertRegex(document_text, r"Product 1.*Product 1 description")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(BytesIO(invoice.document)).replace(
                "\n", ""
            )
            self.assertRegex(document_text, r"Produit 1.*Description du produit 1")

        # - Finally, unknown language should use the default language as fallback
        with switch_language(product, "de-de"):
            document_text = pdf_extract_text(BytesIO(invoice.document)).replace(
                "\n", ""
            )
            self.assertRegex(document_text, r"Product 1.*Product 1 description")

    def test_models_invoice_document_type_invoice(self):
        """
        If invoice type is "invoice", a document of type invoice should be
        generated.
        """
        product = ProductFactory()
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(invoice.document)).replace("\n", "")
        self.assertRegex(document_text, r"INVOICE")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(BytesIO(invoice.document)).replace(
                "\n", ""
            )
            self.assertRegex(document_text, r"FACTURE")

    def test_models_invoice_document_type_credit_note(self):
        """
        If invoice type is "credit_note",
        a document of type credit_note should be generated.
        """
        product = ProductFactory()
        order = OrderFactory(product=product)
        invoice = InvoiceFactory(order=order, total=order.total)
        credit_note = InvoiceFactory(
            order=invoice.order,
            parent=invoice,
            total=-invoice.total,
        )

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(credit_note.document)).replace(
            "\n", ""
        )
        self.assertRegex(document_text, r"CREDIT NOTE")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(BytesIO(credit_note.document)).replace(
                "\n", ""
            )
            self.assertRegex(document_text, r"AVOIR")
