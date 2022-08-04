"""Test suite for the ProformaInvoice model."""
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
from joanie.payment.factories import ProformaInvoiceFactory, TransactionFactory
from joanie.payment.models import ProformaInvoice


class ProformaInvoiceModelTestCase(TestCase):
    """
    Test case for the ProformaInvoice model
    """

    def test_models_proforma_invoice_type_invoice(self):
        """
        If pro forma invoice has a positive amount, its type should be `invoice` and its
        string representation should be prefixed by "Invoice".
        """
        proforma_invoice = ProformaInvoiceFactory(order=OrderFactory(), total=100)

        self.assertEqual(proforma_invoice.type, "invoice")
        self.assertEqual(
            str(proforma_invoice), f"Pro forma Invoice {proforma_invoice.reference}"
        )

    def test_models_proforma_invoice_type_credit_note(self):
        """
        If pro forma invoice has a negative amount, its type should be `credit_note`
        """
        proforma_invoice = ProformaInvoiceFactory(order=OrderFactory(), total=100)
        credit_note = ProformaInvoiceFactory(
            order=proforma_invoice.order, parent=proforma_invoice, total=-100
        )

        self.assertEqual(credit_note.type, "credit_note")
        self.assertEqual(
            str(credit_note), f"Pro forma Credit note {credit_note.reference}"
        )

    def test_models_proforma_invoice_credit_note_with_amount_greater_than_related_invoice_amount(
        self,
    ):
        """
        If a credit note has an amount greater than its parent invoiced balance,
        a ValidationError should be raised.
        """
        # Create an order and its related pro forma invoice for 100.00 €
        order = OrderFactory(product=ProductFactory(price=100))
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)
        # Then link a pro forma invoice for 20.00 €
        ProformaInvoiceFactory(
            order=proforma_invoice.order, parent=proforma_invoice, total=D(20.00)
        )
        # Finally, link a pro forma credit note for -10.00 €
        ProformaInvoiceFactory(
            order=proforma_invoice.order, parent=proforma_invoice, total=D(-10.00)
        )

        # Invoiced balance should be 110.00 €
        self.assertEqual(proforma_invoice.invoiced_balance.amount, D(110.00))

        # Credit a credit note greater than invoiced balance should be forbidden
        with self.assertRaises(ValidationError) as context:
            ProformaInvoiceFactory(order=order, parent=proforma_invoice, total=-111)

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['Credit note amount cannot be greater than its "
                "related pro forma invoice invoiced balance.']}"
            ),
        )

    def test_models_proforma_invoice_normalize_reference(self):
        """
        When a pro forma invoice object is created, its reference should be normalized.
        """
        order = OrderFactory()
        invoice = ProformaInvoiceFactory(reference="1", order=order, total=order.total)

        # Reference should have been normalized using current timestamp and
        # order uid (e.g: f04bca42-1639062573511)
        self.assertIsNotNone(re.fullmatch(r"^[0-9a-f]{8}-\d{13}$", invoice.reference))

    def test_models_proforma_invoice_protected(self):
        """
        Order deletion should be blocked as long as related pro forma invoice exists.
        """
        order = OrderFactory()
        invoice = ProformaInvoiceFactory(order=order, total=order.total)

        with self.assertRaises(ProtectedError):
            invoice.order.delete()

    def test_models_proforma_invoice_balance(self):
        """
        ProformaInvoice.balance should return the current balance
        of the pro forma invoice.
        """
        product = ProductFactory(price=500)
        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)

        # - At beginning, balance should be -500.00
        self.assertEqual(proforma_invoice.balance.amount, D("-500.00"))

        # - Then we received a payment to pay the full order,
        #   balance should be -500.00 + 500.00 = 0.00
        TransactionFactory(total=product.price, proforma_invoice=proforma_invoice)
        proforma_invoice.refresh_from_db()
        self.assertEqual(proforma_invoice.balance.amount, D("0.00"))

        # - Then we create a credit note to refund a part of the order (100.00)
        proforma_credit_note = ProformaInvoiceFactory(
            order=proforma_invoice.order, parent=proforma_invoice, total=-100
        )
        proforma_invoice.refresh_from_db()
        self.assertEqual(proforma_invoice.balance.amount, D("100.00"))

        # - Then we register the transaction to refund the client (100.00)
        TransactionFactory(
            total=Money(-100.00, order.total.currency),
            proforma_invoice=proforma_credit_note,
        )
        proforma_invoice.refresh_from_db()
        self.assertEqual(proforma_invoice.balance.amount, D("0.00"))

    def test_models_proforma_invoice_state_paid(self):
        """
        If pro forma invoice balance is greater or equal than zero, transactions_balance
        and invoiced_balance are not equal to zero, invoice state should be paid
        """
        product = ProductFactory(price="100.00")
        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)
        TransactionFactory.create_batch(
            2, total=product.price / 2, proforma_invoice=proforma_invoice
        )

        with self.assertNumQueries(7):
            self.assertEqual(proforma_invoice.invoiced_balance, order.total)
            self.assertEqual(proforma_invoice.transactions_balance, order.total)
            self.assertEqual(proforma_invoice.balance.amount, D("0.00"))
            self.assertEqual(proforma_invoice.state, "paid")

    def test_models_proforma_invoice_state_refunded(self):
        """
        If pro forma invoice balance is greater or equal than zero, transactions_balance
        and invoiced_balance are equal to zero,
        pro forma invoice state should be refunded
        """
        product = ProductFactory(price="100.00")
        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)
        TransactionFactory.create_batch(
            2, total=product.price / 2, proforma_invoice=proforma_invoice
        )

        # - Fully refund the order
        ProformaInvoiceFactory(
            order=proforma_invoice.order, parent=proforma_invoice, total=-order.total
        )
        TransactionFactory(proforma_invoice=proforma_invoice, total=-product.price)

        with self.assertNumQueries(12):
            self.assertEqual(proforma_invoice.invoiced_balance.amount, D("0.00"))
            self.assertEqual(proforma_invoice.transactions_balance.amount, D("0.00"))
            self.assertEqual(proforma_invoice.balance.amount, D("0.00"))
            self.assertEqual(proforma_invoice.state, "refunded")

    def test_models_proforma_invoice_state_unpaid(self):
        """
        If pro forma invoice balance is less than zero,
        pro forma invoice state should be unpaid.
        """
        product = ProductFactory(price="100.00")
        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)
        TransactionFactory(total=product.price / 2, proforma_invoice=proforma_invoice)

        with self.assertNumQueries(4):
            self.assertEqual(proforma_invoice.balance.amount, D("-50.00"))
            self.assertEqual(proforma_invoice.state, "unpaid")

    def test_models_proforma_invoice_child_cannot_relies_on_another_child(self):
        """
        A pro forma invoice cannot have a parent which is
        a child of another pro forma invoice.
        """
        order = OrderFactory()
        parent = ProformaInvoiceFactory(order=order, total=order.total)
        child = ProformaInvoiceFactory(
            order=parent.order, parent=parent, total=-order.total
        )

        with self.assertRaises(ValidationError) as context:
            ProformaInvoiceFactory(order=child.order, parent=child, total=20.00)

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['Pro forma invoice cannot have as parent "
                "another pro forma invoice which is a child.']}"
            ),
        )

    def test_models_proforma_invoice_relying_on_order_with_a_negative_amount(self):
        """
        A pro forma invoice without parent must have a positive total amount otherwise
        a validation error should be raised on save.
        """
        order = OrderFactory()

        with self.assertRaises(ValidationError) as context:
            ProformaInvoiceFactory(order=order, total=-200.00)

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Credit note must have a parent pro forma invoice.']}",
        )

    def test_models_proforma_invoice_without_parent_unique_per_order(self):
        """
        An order can have only one pro forma invoice without parent
        """
        order = OrderFactory()

        ProformaInvoiceFactory(order=order, total=200.00)

        with self.assertRaises(IntegrityError) as context:
            ProformaInvoiceFactory(order=order, total=100.00)

        self.assertRegex(
            str(context.exception),
            (
                "^duplicate key value violates unique constraint "
                '"only_one_proforma_invoice_without_parent_per_order"'
            ),
        )

    def test_models_proforma_invoice_update_invoice_relying_on_order_with_a_negative_amount(
        self,
    ):
        """
        A pro forma invoice without a parent must have a positive total amount otherwise
        an integrity error should be raised when clean is bypassed.
        """
        order = OrderFactory()
        invoice = ProformaInvoiceFactory(order=order, total=200.00)

        with self.assertRaises(IntegrityError) as context:
            ProformaInvoice.objects.filter(pk=invoice.pk).update(total=-200.00)

        self.assertRegex(
            str(context.exception),
            (
                '"joanie_proforma_invoice" violates check constraint '
                '"main_proforma_invoice_should_have_a_positive_amount"'
            ),
        )

    def test_models_proforma_invoice_localized_context(self):
        """
        When a pro forma invoice is created, localized contexts in each enabled
        languages should be created.
        """
        order = OrderFactory()
        invoice = ProformaInvoiceFactory(order=OrderFactory(), total=order.total)
        languages = settings.LANGUAGES
        self.assertEqual(len(list(invoice.localized_context)), len(languages))

    def test_models_proforma_invoice_get_document_context(self):
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
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)

        context = proforma_invoice.get_document_context("en-us")
        self.assertEqual(context["order"]["product"]["name"], "Product 1")
        self.assertEqual(
            context["order"]["product"]["description"], "Product 1 description"
        )

        context = proforma_invoice.get_document_context("fr-fr")
        self.assertEqual(context["order"]["product"]["name"], "Produit 1")
        self.assertEqual(
            context["order"]["product"]["description"], "Description du produit 1"
        )

        # When translation for the given language does not exist,
        # we should get the fallback language translation.
        context = proforma_invoice.get_document_context("de-de")
        self.assertEqual(context["order"]["product"]["name"], "Product 1")
        self.assertEqual(
            context["order"]["product"]["description"], "Product 1 description"
        )

    def test_models_proforma_invoice_document(self):
        """
        ProformaInvoice document property which should generate a document
        into the active language
        """
        product = ProductFactory(title="Product 1", description="Product 1 description")
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
            description="Description du produit 1",
        )

        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(proforma_invoice.document)).replace(
            "\n", ""
        )
        self.assertRegex(document_text, r"Product 1.*Product 1 description")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(
                BytesIO(proforma_invoice.document)
            ).replace("\n", "")
            self.assertRegex(document_text, r"Produit 1.*Description du produit 1")

        # - Finally, unknown language should use the default language as fallback
        with switch_language(product, "de-de"):
            document_text = pdf_extract_text(
                BytesIO(proforma_invoice.document)
            ).replace("\n", "")
            self.assertRegex(document_text, r"Product 1.*Product 1 description")

    def test_models_proforma_invoice_document_type_invoice(self):
        """
        If pro forma invoice type is "invoice", a document of type invoice should be
        generated.
        """
        product = ProductFactory()
        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(proforma_invoice.document)).replace(
            "\n", ""
        )
        self.assertRegex(document_text, r"INVOICE")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(
                BytesIO(proforma_invoice.document)
            ).replace("\n", "")
            self.assertRegex(document_text, r"FACTURE")

    def test_models_proforma_invoice_document_type_credit_note(self):
        """
        If pro forma invoice type is "credit_note",
        a document of type credit_note should be generated.
        """
        product = ProductFactory()
        order = OrderFactory(product=product)
        proforma_invoice = ProformaInvoiceFactory(order=order, total=order.total)
        proforma_credit_note = ProformaInvoiceFactory(
            order=proforma_invoice.order,
            parent=proforma_invoice,
            total=-proforma_invoice.total,
        )

        # - The default language is used first
        document_text = pdf_extract_text(
            BytesIO(proforma_credit_note.document)
        ).replace("\n", "")
        self.assertRegex(document_text, r"CREDIT NOTE")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with switch_language(product, "fr-fr"):
            document_text = pdf_extract_text(
                BytesIO(proforma_credit_note.document)
            ).replace("\n", "")
            self.assertRegex(document_text, r"AVOIR")
