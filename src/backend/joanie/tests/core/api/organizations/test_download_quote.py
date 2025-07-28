"""Test suite for Organization Download Quote document in PDF bytes."""

from http import HTTPStatus
from io import BytesIO

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiDownloadQuoteTest(BaseAPITestCase):
    """Test suite for Organization Download Quote document in PDF bytes."""

    def test_api_organization_download_quote_anonymous(self):
        """
        Anonymous user should not be able to download the quote of a batch order from an
        organization.
        """
        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED, organization=organization
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/download-quote/",
            data={"quote_id": str(batch_order.quote.id)},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_organization_download_quote_create(self):
        """
        Authenticated user should not be able to create a quote on the download endpoint.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/download-quote/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"quote_id": str(quote.id)},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_download_quote_update(self):
        """
        Authenticated user should not be able to update a quote on the download endpoint.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/download-quote/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"quote_id": str(quote.id)},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_download_quote_partially_update(self):
        """
        Authenticated user should not be able to partially update a quote on the download endpoint.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/download-quote/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"quote_id": str(quote.id)},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_download_quote_delete(self):
        """
        Authenticated user should not be able to delete a quote on the download endpoint.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/download-quote/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"quote_id": str(quote.id)},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_download_quote_not_owned(self):
        """
        Authenticated user of an organization should not be able to download the quote of another
        organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/download-quote/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"quote_id": str(quote.id)},
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_organization_download_quote_authenticated_with_organization_access(
        self,
    ):
        """
        Authenticated user with organization access that is not owner should not be able to
        download the quote document.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        # Check every existing roles except 'owner'
        for role in [
            role[0]
            for role in models.OrganizationAccess.ROLE_CHOICES
            if role[0] != enums.OWNER
        ]:
            access = factories.UserOrganizationAccessFactory(
                organization=batch_order.organization, role=role
            )
            token = self.generate_token_from_user(access.user)

            quote = batch_order.quote

            response = self.client.get(
                f"/api/v1.0/organizations/{str(batch_order.organization.id)}/download-quote/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data={"quote_id": str(quote.id)},
            )

            self.assertEqual(
                response.status_code, HTTPStatus.FORBIDDEN, response.json()
            )

    def test_api_organization_download_quote_authenticated_and_with_organization_permission(
        self,
    ):
        """
        Authenticated user with organization access with owner role should be able to download
        the quote in PDF.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)
        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role="owner"
        )
        token = self.generate_token_from_user(access.user)

        quote = batch_order.quote

        expected_filename = f"{quote.definition.title}-{quote.id}".replace(" ", "_")

        response = self.client.get(
            f"/api/v1.0/organizations/{str(batch_order.organization.id)}/download-quote/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"quote_id": str(quote.id)},
        )

        document_text = pdf_extract_text(BytesIO(b"".join(response.streaming_content)))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{expected_filename}.pdf"',
        )
        self.assertIn(quote.definition.title, document_text)
        self.assertIn(quote.batch_order.owner.get_full_name(), document_text)
        self.assertIn("Company", document_text)
