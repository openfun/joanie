"""Test suite for the Quote API client viewset"""

from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class QuoteApiTest(BaseAPITestCase):
    """Test suite for Quote API client viewset."""

    # List
    def test_api_quotes_list_anonymous(self):
        """Anonymous user cannot list quotes."""
        response = self.client.get(
            "/api/v1.0/quotes/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_quotes_list_not_owned(self):
        """Authenticated user should not be able to list the quote where he is not the owner."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.BatchOrderFactory.create_batch(2)

        response = self.client.get(
            "/api/v1.0/quotes/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
        )

    def test_api_quotes_list_authenticated(self):
        """Authenticated user can list quotes where he is the owner."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Create quotes of batch orders
        factories.BatchOrderFactory.create_batch(
            2, owner=user, state=enums.BATCH_ORDER_STATE_QUOTED
        )

        response = self.client.get(
            "/api/v1.0/quotes/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        quotes = models.Quote.objects.filter(
            batch_order__owner=user,
            batch_order__state=enums.BATCH_ORDER_STATE_QUOTED,
        )
        expected_quotes = sorted(quotes, key=lambda x: x.created_on, reverse=True)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
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
                            "relation_id": str(quote.batch_order.relation.id),
                            "state": quote.batch_order.state,
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
        )

    # Detail
    def test_api_quotes_retrieve_anonymous(self):
        """Anonymous user cannot retrieve a quote."""
        quote = factories.QuoteFactory()

        response = self.client.get(
            f"/api/v1.0/quotes/{quote.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_quotes_retrieve_authenticated_invalid_id(self):
        """
        Authenticated user cannot retrieve a quote with an invalid id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/quotes/invalid_id/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

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

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_quotes_retrieve_authenticated(self):
        """
        Authenticated user should be able to retrieve a quote if he is the owner
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            owner=user,
        )

        response = self.client.get(
            f"/api/v1.0/quotes/{batch_order.quote.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(
            response.json(),
            {
                "id": str(batch_order.quote.id),
                "batch_order": {
                    "owner_name": batch_order.quote.batch_order.owner.name,
                    "company_name": batch_order.quote.batch_order.company_name,
                    "id": str(batch_order.quote.batch_order.id),
                    "organization_id": str(
                        batch_order.quote.batch_order.organization.id
                    ),
                    "relation_id": str(batch_order.quote.batch_order.relation.id),
                    "state": batch_order.quote.batch_order.state,
                },
                "definition": {
                    "body": batch_order.quote.definition.body,
                    "description": batch_order.quote.definition.description,
                    "id": str(batch_order.quote.definition.id),
                    "language": batch_order.quote.definition.language,
                    "name": batch_order.quote.definition.name,
                    "title": batch_order.quote.definition.title,
                },
                "has_purchase_order": False,
                "organization_signed_on": None,
            },
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

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_quotes_partially_update_not_allowed(self):
        """Authenticated user should not be able to partially update a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.patch(
            "/api/v1.0/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_quotes_update_not_allowed(self):
        """Authenticated user should not be able to update a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.put(
            "/api/v1.0/quotes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={},
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_quotes_delete_not_allowed(self):
        """Authenticated user should not be able to delete a quote."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        quote = factories.QuoteFactory()

        response = self.client.delete(
            f"/api/v1.0/quotes/{quote.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )
