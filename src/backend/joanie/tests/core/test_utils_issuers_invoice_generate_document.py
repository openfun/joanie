"""Test suite for utility method to generate an invoice in PDF bytes format."""
from io import BytesIO

from django.test import TestCase
from django.utils.translation import override

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core.factories import ProductFactory
from joanie.core.utils import issuers
from joanie.payment import enums as payment_enums
from joanie.payment.factories import InvoiceFactory


class UtilsIssuersInvoiceGenerateDocumentTestCase(TestCase):
    """Test suite for utility method to generate invoice document in PDF bytes format."""

    def test_utils_issuers_generate_document(self):
        """
        Using the issuer to generate an invoice document in PDF bytes format.
        The context should be set in the active language.
        """
        product = ProductFactory(title="Product 1", description="Product 1 description")
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
            description="Description du produit 1",
        )
        invoice = InvoiceFactory(order__product=product, total=product.price)

        file_bytes = issuers.generate_document(
            name=payment_enums.INVOICE_TYPE_INVOICE,
            context=invoice.get_document_context(),
        )

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
        self.assertRegex(document_text, r"Product 1.*Product 1 description")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with override("fr-fr", deactivate=True):
            file_bytes = issuers.generate_document(
                name=payment_enums.INVOICE_TYPE_INVOICE,
                context=invoice.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
            self.assertRegex(document_text, r"Produit 1.*Description du produit 1")

        # # - Finally, unknown language should use the default language as fallback
        with override("de-de", deactivate=True):
            file_bytes = issuers.generate_document(
                name=payment_enums.INVOICE_TYPE_INVOICE,
                context=invoice.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
            self.assertRegex(document_text, r"Product 1.*Product 1 description")

    def test_utils_issuers_generate_document_type_invoice(self):
        """
        If invoice type is "invoice", a document of type invoice should be generated.
        """
        invoice = InvoiceFactory()

        file_bytes = issuers.generate_document(
            name=payment_enums.INVOICE_TYPE_INVOICE,
            context=invoice.get_document_context(),
        )

        # - The default language is used first
        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
        self.assertRegex(document_text, r"INVOICE")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with override("fr-fr", deactivate=True):
            file_bytes = issuers.generate_document(
                name=payment_enums.INVOICE_TYPE_INVOICE,
                context=invoice.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
            self.assertRegex(document_text, r"FACTURE")

    def test_utils_issuers_generate_document_type_credit_note(self):
        """
        If invoice type is "credit_note", a document of type credit_note should be generated.
        """
        invoice = InvoiceFactory()
        credit_note = InvoiceFactory(
            order=invoice.order,
            parent=invoice,
            total=-invoice.total,
        )

        # - The default language is used first
        file_bytes = issuers.generate_document(
            name=payment_enums.INVOICE_TYPE_INVOICE,
            context=credit_note.get_document_context(),
        )

        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
        self.assertRegex(document_text, r"CREDIT NOTE")

        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with override("fr-fr", deactivate=True):
            file_bytes = issuers.generate_document(
                name=payment_enums.INVOICE_TYPE_INVOICE,
                context=credit_note.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
            self.assertRegex(document_text, r"AVOIR")

    def test_utils_issuers_generate_document_into_active_language(self):
        """
        Invoice generate document method should generate a document into the active language.
        """
        product = ProductFactory(title="Product 1", description="Product 1 description")
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
            description="Description du produit 1",
        )
        invoice = InvoiceFactory(order__product=product, total=product.price)

        # - The default language is used first
        file_bytes = issuers.generate_document(
            name=payment_enums.INVOICE_TYPE_INVOICE,
            context=invoice.get_document_context(),
        )

        document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
        self.assertRegex(document_text, r"Product 1.*Product 1 description")
        # - Then if we switch to an existing language, it should generate
        #   a document with the context in the active language
        with override("fr-fr", deactivate=True):
            file_bytes = issuers.generate_document(
                name=payment_enums.INVOICE_TYPE_INVOICE,
                context=invoice.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
            self.assertRegex(document_text, r"Produit 1.*Description du produit 1")

        # - Finally, unknown language should use the default language as fallback
        with override("de-de", deactivate=True):
            file_bytes = issuers.generate_document(
                name=payment_enums.INVOICE_TYPE_INVOICE,
                context=invoice.get_document_context(),
            )
            document_text = pdf_extract_text(BytesIO(file_bytes)).replace("\n", "")
            self.assertRegex(document_text, r"Product 1.*Product 1 description")
