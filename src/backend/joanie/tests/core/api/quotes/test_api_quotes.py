"""Test suite for the Quote API client viewset"""

from http import HTTPStatus
from unittest import mock

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class QuoteApiTest(BaseAPITestCase):
    """Test suite for Quote API client viewset."""

    # List
    def test_api_quotes_list_anonymous(self):
        """Anonymous user cannot list quotes."""
        response = self.client.get(
            "/api/v1.0/quotes/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_quotes_list_not_owned(self):
        """Authenticated user should not be able to list the quote where he is not the owner."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.BatchOrderFactory.create_batch(2)

        response = self.client.get(
            "/api/v1.0/quotes/", HTTP_AUTHORIZATION=f"Bearer {token}"
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
    def test_api_quotes_list_authenticated(self, _mock_thumbnail):
        """Authenticated user can list quotes where he is the owner."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Create quotes of batch orders
        factories.BatchOrderFactory.create_batch(
            2,
            owner=user,
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        response = self.client.get(
            "/api/v1.0/quotes/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        quotes = models.Quote.objects.filter(
            batch_order__owner=user,
        ).order_by("-created_on")

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 2,
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
                            "payment_method": enums.BATCH_ORDER_WITH_BANK_TRANSFER,
                            "contract_submitted": False,
                        },
                        "has_purchase_order": False,
                        "organization_signed_on": None,
                    }
                    for quote in quotes
                ],
            },
            response.json(),
        )

    # Detail
    def test_api_quotes_retrieve_anonymous(self):
        """Anonymous user cannot retrieve a quote."""
        quote = factories.QuoteFactory()

        response = self.client.get(
            f"/api/v1.0/quotes/{quote.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_quotes_retrieve_authenticated_invalid_id(self):
        """
        Authenticated user cannot retrieve a quote with an invalid id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/quotes/invalid_id/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_quotes_retrieve_authenticated_not_owned(self):
        """
        Authenticated user cannot retrieve a quote if he is not the owner.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        quote = factories.QuoteFactory()

        response = self.client.get(
            f"/api/v1.0/quotes/{quote.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_quotes_retrieve_authenticated(self, _mock_thumbnail):
        """
        Authenticated user should be able to retrieve a quote if he is the owner
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_TO_SIGN,
            owner=user,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        response = self.client.get(
            f"/api/v1.0/quotes/{batch_order.quote.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(
            {
                "id": str(batch_order.quote.id),
                "batch_order": {
                    "owner_name": batch_order.quote.batch_order.owner.name,
                    "company_name": batch_order.quote.batch_order.company_name,
                    "id": str(batch_order.quote.batch_order.id),
                    "organization_id": str(
                        batch_order.quote.batch_order.organization.id
                    ),
                    "relation": {
                        "id": str(batch_order.offering.id),
                        "course": {
                            "id": str(batch_order.offering.course.id),
                            "title": batch_order.offering.course.title,
                            "code": batch_order.offering.course.code,
                            "cover": "_this_field_is_mocked",
                        },
                        "product": {
                            "id": str(batch_order.offering.product.id),
                            "title": batch_order.offering.product.title,
                        },
                    },
                    "state": batch_order.quote.batch_order.state,
                    "payment_method": enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
                    "contract_submitted": True,
                },
                "has_purchase_order": True,
                "organization_signed_on": format_date(
                    batch_order.quote.organization_signed_on
                ),
            },
            response.json(),
        )

    def test_api_quotes_create_not_allowed(self):
        """Authenticated user should not be able to create a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_quotes_partially_update_not_allowed(self):
        """Authenticated user should not be able to partially update a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.patch(
            "/api/v1.0/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_quotes_update_not_allowed(self):
        """Authenticated user should not be able to update a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.put(
            "/api/v1.0/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_quotes_delete_not_allowed(self):
        """Authenticated user should not be able to delete a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        quote = factories.QuoteFactory()

        response = self.client.delete(
            f"/api/v1.0/quotes/{quote.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)
