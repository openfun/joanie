"""Tests for the Order invoice API."""

from http import HTTPStatus
from io import BytesIO

from django.core.cache import cache

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import factories
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase


class OrderInvoiceApiTest(BaseAPITestCase):
    """Test the API of the Order invoice endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_get_invoice_anonymous(self):
        """An anonymous user should not be allowed to retrieve an invoice."""
        invoice = InvoiceFactory()

        response = self.client.get(
            (
                f"/api/v1.0/orders/{invoice.order.id}/invoice/"
                f"?reference={invoice.reference}"
            ),
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_get_invoice_authenticated_user_with_no_reference(self):
        """
        If an authenticated user tries to retrieve order's invoice
        without reference parameter, it should return a bad request response.
        """
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(invoice.order.owner)

        response = self.client.get(
            f"/api/v1.0/orders/{invoice.order.id}/invoice/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertDictEqual(
            response.json(), {"reference": "This parameter is required."}
        )

    def test_api_order_get_invoice_authenticated_not_linked_to_order(self):
        """
        An authenticated user should not be allowed to retrieve an invoice
        not linked to the current order
        """
        user = factories.UserFactory()
        order = factories.OrderFactory()
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            (f"/api/v1.0/orders/{order.id}/invoice/" f"?reference={invoice.reference}"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertEqual(
            response.json(),
            (
                f"No invoice found for order {order.id} "
                f"with reference {invoice.reference}."
            ),
        )

    def test_api_order_get_invoice_authenticated_user_not_owner(self):
        """
        An authenticated user should not be allowed to retrieve
        an invoice not owned by himself
        """
        user = factories.UserFactory()
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            (
                f"/api/v1.0/orders/{invoice.order.id}/invoice/"
                f"?reference={invoice.reference}"
            ),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertEqual(
            response.json(),
            (
                f"No invoice found for order {invoice.order.id} "
                f"with reference {invoice.reference}."
            ),
        )

    def test_api_order_get_invoice_authenticated_owner(self):
        """
        An authenticated user which owns the related order should be able to retrieve
        a related invoice through its reference
        """
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(invoice.order.owner)

        response = self.client.get(
            (
                f"/api/v1.0/orders/{invoice.order.id}/invoice/"
                f"?reference={invoice.reference}"
            ),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={invoice.reference}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"INVOICE")
