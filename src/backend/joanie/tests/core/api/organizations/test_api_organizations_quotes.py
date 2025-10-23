"""Test suite for the Organizations Quote API"""

from http import HTTPStatus
from unittest import mock

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class OrganizationQuoteApiTest(BaseAPITestCase):
    """Test suite for the Organizations Quote API"""

    maxDiff = None

    def test_api_organizations_quotes_list_anonymous(self):
        """
        Anonymous user cannot query all quotes from an organization.
        """
        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organization_quotes_list_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        organization's quotes
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.BatchOrderFactory.create_batch(
            3, state=enums.BATCH_ORDER_STATE_QUOTED
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
            response.json(),
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organizations_quotes_list_with_accesses(self, _mock_thumbnail):
        """
        Authenticated user with access to the organization can query organization's quotes
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        # Create 3 batch order with organization access of requesting user
        factories.BatchOrderFactory.create_batch(
            3, state=enums.BATCH_ORDER_STATE_QUOTED, organization=organization
        )
        # Canceled batch order are excluded
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED, organization=organization
        )
        batch_order.flow.cancel()
        # Create random batch orders that should not be returned
        factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
        )

        quotes = models.Quote.objects.filter(
            batch_order__organization=organization,
            batch_order__state=enums.BATCH_ORDER_STATE_QUOTED,
        )
        expected_quotes = sorted(quotes, key=lambda x: x.created_on, reverse=True)

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(quote.id),
                        "batch_order": {
                            "owner_name": quote.batch_order.owner.name,
                            "company_name": quote.batch_order.company_name,
                            "id": str(quote.batch_order.id),
                            "organization_id": str(quote.batch_order.organization.id),
                            "relation": {
                                "id": str(quote.batch_order.offering.id),
                                "course": {
                                    "id": str(quote.batch_order.offering.course.id),
                                    "title": quote.batch_order.offering.course.title,
                                    "code": quote.batch_order.offering.course.code,
                                    "cover": "_this_field_is_mocked",
                                },
                                "product": {
                                    "id": str(quote.batch_order.offering.product.id),
                                    "title": quote.batch_order.offering.product.title,
                                },
                            },
                            "state": quote.batch_order.state,
                            "payment_method": enums.BATCH_ORDER_WITH_CARD_PAYMENT,
                            "contract_submitted": False,
                        },
                        "definition": {
                            "body": quote.definition.body,
                            "description": quote.definition.description,
                            "id": str(quote.definition.id),
                            "language": quote.definition.language,
                            "name": quote.definition.name,
                            "title": quote.definition.title,
                        },
                        "has_purchase_order": False,
                        "organization_signed_on": None,
                    }
                    for quote in expected_quotes
                ],
            },
            response.json(),
        )

    def test_api_organizations_quotes_create_anonymous(self):
        """
        Anonymous user should not be able to create an organization's quote
        """
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_quotes_create_authenticated(self):
        """
        Authenticated user should not be able to create an organization's quote
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_quotes_update_anonymous(self):
        """
        Anonymous user should not be able to update an organization's quote
        """
        organization = factories.OrganizationFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_quotes_update_authenticated(self):
        """
        Authenticated user should not be able to update an organization's quote
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_quotes_patch_anonymous(self):
        """
        Anonymous user should not be able to partially update an organization's quote
        """
        organization = factories.OrganizationFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_quotes_patch_authenticated(self):
        """
        Authenticated user should not be able to partially update an organization's quote
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_quotes_delete_anonymous(self):
        """
        Anonymous user should not be able to delete an organization's quote
        """
        organization = factories.OrganizationFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_quotes_delete_authenticated(self):
        """
        Authenticated user should not be able to delete an organization's quote
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{str(organization.id)}/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organization_quotes_retrieve_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        organization's quotes
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_orders = factories.BatchOrderFactory.create_batch(
            3, state=enums.BATCH_ORDER_STATE_QUOTED
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{str(organization.id)}/"
            f"quotes/{str(batch_orders[0].quote.id)}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organizations_quotes_retrieve_with_accesses(self, _mock_thumbnail):
        """
        Authenticated user with access to the organization can retrieve an organization's quote
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_TO_SIGN, organization=organization
        )
        quote = batch_order.quote

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/quotes/{quote.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "id": str(quote.id),
                "batch_order": {
                    "owner_name": quote.batch_order.owner.name,
                    "company_name": quote.batch_order.company_name,
                    "id": str(quote.batch_order.id),
                    "organization_id": str(quote.batch_order.organization.id),
                    "relation": {
                        "id": str(quote.batch_order.offering.id),
                        "course": {
                            "id": str(quote.batch_order.offering.course.id),
                            "title": quote.batch_order.offering.course.title,
                            "code": quote.batch_order.offering.course.code,
                            "cover": "_this_field_is_mocked",
                        },
                        "product": {
                            "id": str(quote.batch_order.offering.product.id),
                            "title": quote.batch_order.offering.product.title,
                        },
                    },
                    "state": quote.batch_order.state,
                    "payment_method": enums.BATCH_ORDER_WITH_CARD_PAYMENT,
                    "contract_submitted": True,
                },
                "definition": {
                    "body": quote.definition.body,
                    "description": quote.definition.description,
                    "id": str(quote.definition.id),
                    "language": quote.definition.language,
                    "name": quote.definition.name,
                    "title": quote.definition.title,
                },
                "has_purchase_order": False,
                "organization_signed_on": format_date(quote.organization_signed_on),
            },
            response.json(),
        )

    def test_api_organizations_quotes_retrieve_with_accesses_using_organization_code(
        self,
    ):
        """
        Authenticated user with access to the organization can query an organization's quotes
        by using the organization's code into the api endpoint.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        # Create 3 batch order with organization access of requesting user
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED, organization=organization
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.code}/quotes/{batch_order.quote.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
