"""Test suite to confirm quote endpoint for organization client API"""

from decimal import Decimal
from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiConfirmQuoteTest(BaseAPITestCase):
    """Test suite for Organization Download Quote document in PDF bytes."""

    def test_api_organization_confirm_quote_anonymous(self):
        """Anonymous user should not be able to confirm a quote."""
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote.id),
                "total": "123.45",
            },
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organization_confirm_quote_get(self):
        """Authenticated user should not be able to confirm a quote with the get method"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote.id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organization_confirm_quote_create(self):
        """Authenticated user should not be able to confirm a quote with the post method"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote.id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organization_confirm_quote_put(self):
        """Authenticated user should not be able to confirm a quote with the put method"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote.id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organization_confirm_quote_delete(self):
        """Authenticated user should not be able to confirm a quote with the delete method"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote.id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organization_confirm_quote_invalid_id(self):
        """Authenticated user should not be able to confirm a quote with an invalid id."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": "invalid_id",
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_organization_confirm_quote_not_owned(self):
        """
        Authenticated user should not be able to confirm a quote that his organization does not
        own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
        )

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-quote/",
            data={
                "quote_id": str(batch_order.quote.id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_organization_confirm_quote_organization_access_but_not_owner_role_or_admin_role(
        self,
    ):
        """
        Authenticated user with organization access that is neither owner nor admin role should not
        be able to confirm a quote if the total is missing.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
        )

        for role in [
            role[0]
            for role in models.OrganizationAccess.ROLE_CHOICES
            if role[0] not in [enums.OWNER, enums.ADMIN]
        ]:
            access = factories.UserOrganizationAccessFactory(
                organization=batch_order.organization, role=role
            )
            token = self.generate_token_from_user(access.user)

            response = self.client.patch(
                f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-quote/",
                data={
                    "quote_id": str(batch_order.quote.id),
                    "total": "123.45",
                },
                HTTP_AUTHORIZATION=f"Bearer {token}",
                content_type="application/json",
            )

            self.assertEqual(
                response.status_code, HTTPStatus.FORBIDDEN, response.json()
            )

    def test_api_organization_confirm_quote_authenticated_missing_total_should_fail(
        self,
    ):
        """
        Authenticated user with organization access and an owner role should not be able to
        confirm a quote if the total is missing.
        """
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)
        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-quote/",
            data={
                "quote_id": str(batch_order.quote.id),
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

    def test_api_organization_confirm_quote_canceled_batch_order(self):
        """
        Authenticated user with owner role should not be able to confirm a quote
        if the batch order is canceled.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
        )
        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)
        quote_id = batch_order.quote.id

        # Cancel the batch order after it has been quoted
        batch_order.flow.cancel()
        batch_order.refresh_from_db()

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote_id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            {"detail": "Batch order is canceled, cannot confirm quote signature."},
            response.json(),
        )

    def test_api_organization_confirm_quote_no_quote(self):
        """
        Authenticated user with owner role should not be able to confirm a quote
        if the batch order has no quote generated yet.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
        )
        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        # Remove the quote to simulate no quote generated
        quote_id = batch_order.quote.id
        batch_order.quote.delete()
        batch_order.refresh_from_db()

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-quote/",
            data={
                "quote_id": str(quote_id),
                "total": "123.45",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_organization_confirm_quote_already_signed(self):
        """
        Authenticated user with owner role should not be able to confirm a quote
        if the quote is already signed by the organization and total is frozen.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=1,
            state=enums.BATCH_ORDER_STATE_QUOTED,
        )
        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        # Confirm the quote a first time
        batch_order.freeze_total(Decimal("1234.56"))

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-quote/",
            data={
                "quote_id": str(batch_order.quote.id),
                "total": "1234.56",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            {"detail": "Quote is already signed, and total is frozen."}, response.json()
        )

    def test_api_organization_confirm_quote_authenticated(self):
        """
        Authenticated user with owner role in his organization should be able to confirm a quote
        if he has access to the organization and adds the total into the payload.
        It should confirm the quote as signed by the organization, it also adds the value
        on the batch order `total` field. When the batch order's payment method is purchase order,
        the state stays `quoted`, otherwise it can transition to `to_sign`.
        """
        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    nb_seats=1,
                    state=enums.BATCH_ORDER_STATE_QUOTED,
                    payment_method=payment_method,
                )
                access = factories.UserOrganizationAccessFactory(
                    organization=batch_order.organization, role=enums.OWNER
                )
                token = self.generate_token_from_user(access.user)

                response = self.client.patch(
                    f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-quote/",
                    data={"quote_id": str(batch_order.quote.id), "total": "1234.56"},
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                    content_type="application/json",
                )

                batch_order.refresh_from_db()

                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                self.assertEqual(batch_order.total, Decimal("1234.56"))
                self.assertIsNotNone(batch_order.quote.organization_signed_on)

                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)
                else:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)
