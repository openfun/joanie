"""Test suite to confirm purchase order endpoint for organization client API"""

from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiConfirmPurchaseOrderTest(BaseAPITestCase):
    """Test suite for Organization confirm purchase order of the quote"""

    def test_api_organization_confirm_purchase_order_anonymous(self):
        """Anonymous user should not be able to confirm a purchase order."""
        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": quote.id},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_organization_confirm_purchase_order_get(self):
        """Authenticated user should not be able to confirm a purchase order with the get method"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_purchase_order_create(self):
        """
        Authenticated user should not be able to confirm a purchase order with the post method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_purchase_order_put(self):
        """Authenticated user should not be able to confirm a purchase order with the put method"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_purchase_order_delete(self):
        """
        Authenticated user should not be able to confirm a purchase order with the delete method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_purchase_order_invalid_id(self):
        """
        Authenticated user should not be able to confirm a purchase order with an invalid id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": "invalid_id"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_organization_confirm_purchase_order_not_owned(self):
        """
        Authenticated user should not be able to confirm a purchase order that his
        organization does not own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        quote = factories.QuoteFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_organization_confirm_purchase_order_not_owner_role(
        self,
    ):
        """
        Authenticated user with organization access that is not owner should not be able to
        confirm a purchase order.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        for role in [
            role[0]
            for role in models.OrganizationAccess.ROLE_CHOICES
            if role[0] != enums.OWNER
        ]:
            access = factories.UserOrganizationAccessFactory(
                organization=batch_order.organization, role=role
            )
            token = self.generate_token_from_user(access.user)

            response = self.client.patch(
                f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-purchase-order/",
                data={
                    "quote_id": str(batch_order.quote.id),
                },
                HTTP_AUTHORIZATION=f"Bearer {token}",
                content_type="application/json",
            )

            self.assertEqual(
                response.status_code, HTTPStatus.FORBIDDEN, response.json()
            )

    def test_api_organization_confirm_purchase_order_organization_not_signed(self):
        """
        Authenticated user with permission to confirm a purchase order cannot confirm it if the
        quote is not yet signed by the organization.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=1,
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        quote = batch_order.quote
        quote.organization_signed_on = None
        quote.save()

        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_api_organization_confirm_purchase_order_has_purchase_order(self):
        """
        Authenticated user with permission cannot confirm the purchase order if the
        purchase order was already confirmed.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=1,
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        quote = batch_order.quote
        quote.tag_organization_signed_on()
        quote.tag_has_purchase_order()

        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_api_organization_confirm_purchase_order_but_payment_method_other_than_purchase_order(
        self,
    ):
        """
        Authenticated user with the permission cannot confirm a purchase order if the payment
        method of the batch order is other than `purchase_order`.
        """

        for payment_method in [
            payment_method[0]
            for payment_method in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES
            if payment_method[0] != enums.BATCH_ORDER_WITH_PURCHASE_ORDER
        ]:
            batch_order = factories.BatchOrderFactory(
                nb_seats=1,
                state=enums.BATCH_ORDER_STATE_QUOTED,
                payment_method=payment_method,
            )
            quote = batch_order.quote
            quote.tag_organization_signed_on()
            quote.tag_has_purchase_order()

            access = factories.UserOrganizationAccessFactory(
                organization=batch_order.organization, role=enums.OWNER
            )
            token = self.generate_token_from_user(access.user)

            response = self.client.patch(
                f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-purchase-order/",
                data={"quote_id": str(quote.id)},
                HTTP_AUTHORIZATION=f"Bearer {token}",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_api_organization_confirm_purchase_order_authenticated(self):
        """
        Authenticated user with owner role in his organization should be able to confirm a
        purchase order when he has access to the organization, the batch order payment method
        is by purchase order and the quote is signed by the organization.
        The batch order should transition from `quoted` to `to_sign` state.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=1,
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        quote = batch_order.quote
        quote.tag_organization_signed_on()

        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        response = self.client.patch(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-purchase-order/",
            data={"quote_id": str(quote.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
        )

        quote.refresh_from_db()
        batch_order.refresh_from_db()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(quote.has_purchase_order, True)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)
