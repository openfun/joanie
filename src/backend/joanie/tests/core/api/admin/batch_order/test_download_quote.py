"""Test suite for download quote of BatchOrderViewset Admin API endpoint"""

from http import HTTPStatus
from io import BytesIO

from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminDownloadQuoteApiTestCase(BaseAPITestCase):
    """Test suite for download quote of BatchOrderViewset API endpoint"""

    def test_api_admin_batch_order_download_quote_anonymous(self):
        """Anonymous user should not be able to download the quote of a batch order."""

        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_order_download_quote_lambda_user(self):
        """Lambda user should not be able to download the quote of a batch order."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_order_download_quote_post_method(self):
        """
        Authenticated admin user should not be able to use the POST method to download
        the quote of a batch order.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_download_quote_put_method(self):
        """
        Authenticated admin user should not be able to use the PUT method to download
        the quote of a batch order.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_download_quote_patch_method(self):
        """
        Authenticated admin user should not be able to use the PATCH method to download
        the quote of a batch order.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_download_quote_delete_method(self):
        """
        Authenticated admin user should not be able to use the DELETE method to download
        the quote of a batch order.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.delete(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_download_quote_invalid_id(self):
        """
        Authenticated admin user should not be able to download a quote when passing an
        invalid id, it should raise a 404 Not Found error.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/invalid_id/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_admin_batch_order_download_quote_no_total_set(self):
        """
        Authenticated admin user should not be able to download the quote when the total
        on the batch order is not set, it should raise a 400 Bad Request error.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_admin_batch_order_download_quote_staff_user(self):
        """Staff user should be able to download the quote of a batch order."""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)
        batch_order.freeze_total("100.00")

        quote = batch_order.quote
        expected_filename = f"{quote.definition.title}-{quote.id}".replace(" ", "_")

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        date_now = timezone.now().date().strftime("%m/%d/%Y")
        document_text = pdf_extract_text(BytesIO(b"".join(response.streaming_content)))

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{expected_filename}.pdf"',
        )
        self.assertIn(quote.definition.title, document_text)
        self.assertIn("Quote issued on", document_text)
        self.assertIn("100.00", document_text)
        self.assertIn(date_now, document_text)

    def test_api_admin_batch_order_download_quote_admin_authenticated(self):
        """
        Authenticated admin user should be able to download the quote when the total
        on the batch order is set. We should see the total in the document's text.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)
        batch_order.freeze_total("100.00")

        quote = batch_order.quote
        expected_filename = f"{quote.definition.title}-{quote.id}".replace(" ", "_")

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/download-quote/",
            content_type="application/json",
        )

        date_now = timezone.now().date().strftime("%m/%d/%Y")
        document_text = pdf_extract_text(BytesIO(b"".join(response.streaming_content)))

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{expected_filename}.pdf"',
        )
        self.assertIn(quote.definition.title, document_text)
        self.assertIn("Quote issued on", document_text)
        self.assertIn("100.00", document_text)
        self.assertIn(date_now, document_text)
