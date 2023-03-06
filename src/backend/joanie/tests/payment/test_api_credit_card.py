"""
Test suite for the Credit Card API
"""
from unittest import mock

from django.test.utils import override_settings

import arrow
from rest_framework.pagination import PageNumberPagination

from joanie.core.factories import UserFactory
from joanie.core.models import User
from joanie.payment.factories import CreditCardFactory
from joanie.tests.base import BaseAPITestCase


# pylint: disable=too-many-public-methods
class CreditCardAPITestCase(BaseAPITestCase):
    """Manage user's credit cards API test cases"""

    def test_api_credit_card_get_credit_cards_without_authorization(self):
        """Retrieve credit cards without authorization header is forbidden."""
        response = self.client.get("/api/v1.0/credit-cards/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_credit_card_get_credit_cards_with_bad_token(self):
        """Retrieve credit cards with bad token is forbidden."""
        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION="Bearer invalid_token"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "token_not_valid")

    def test_api_credit_card_get_credit_cards_with_expired_token(self):
        """Retrieve credit cards with an expired token is forbidden."""
        token = self.get_user_token(
            "johndoe",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "token_not_valid")

    def test_api_credit_card_get_credit_cards_for_new_user(self):
        """
        Retrieve credit cards of a non existing user is allowed but
        create an user first.
        """
        username = "johndoe"
        self.assertFalse(User.objects.filter(username=username).exists())
        token = self.get_user_token(username)
        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"count": 0, "next": None, "previous": None, "results": []}
        )
        self.assertTrue(User.objects.filter(username=username).exists())

    def test_api_credit_card_get_credit_cards_list(self):
        """Retrieve all authenticated user's credit cards is allowed."""
        user = UserFactory()
        token = self.get_user_token(user.username)
        cards = CreditCardFactory.create_batch(2, owner=user)

        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        results = content.pop("results")
        cards.sort(key=lambda card: card.created_on, reverse=True)
        self.assertEqual(
            [result["id"] for result in results], [str(card.id) for card in cards]
        )
        self.assertEqual(
            content,
            {
                "count": 2,
                "next": None,
                "previous": None,
            },
        )

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_credit_card_read_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""
        user = UserFactory()
        token = self.get_user_token(user.username)
        cards = CreditCardFactory.create_batch(3, owner=user)
        card_ids = [str(card.id) for card in cards]

        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"], "http://testserver/api/v1.0/credit-cards/?page=2"
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            card_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            "/api/v1.0/credit-cards/?page=2", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"], "http://testserver/api/v1.0/credit-cards/"
        )

        self.assertEqual(len(content["results"]), 1)
        card_ids.remove(content["results"][0]["id"])
        self.assertEqual(card_ids, [])

    def test_api_credit_card_get_credit_card(self):
        """Retrieve authenticated user's credit card by its id is allowed."""
        user = UserFactory()
        token = self.get_user_token(user.username)
        card = CreditCardFactory(owner=user)

        response = self.client.get(
            f"/api/v1.0/credit-cards/{card.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)

        # - All fields except token has been serialized
        self.assertEqual(
            response.data,
            {
                "id": str(card.id),
                "title": card.title,
                "brand": card.brand,
                "expiration_month": card.expiration_month,
                "expiration_year": card.expiration_year,
                "last_numbers": card.last_numbers,
                "is_main": card.is_main,
            },
        )

    def test_api_credit_card_get_non_existing_credit_card(self):
        """Retrieve a non existing credit card should return a 404."""
        user = UserFactory()
        token = self.get_user_token(user.username)
        card = CreditCardFactory.build(owner=user)

        response = self.client.get(
            f"/api/v1.0/credit-cards/{card.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 404)

    def test_api_credit_card_get_not_owned_credit_card(self):
        """
        Retrieve credit card don't owned by the
        authenticated user should return a 404.
        """
        user = UserFactory()
        token = self.get_user_token(user.username)
        card = CreditCardFactory()

        response = self.client.get(
            f"/api/v1.0/credit-cards/{card.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 404)

    def test_api_credit_card_create_credit_card_is_not_allowed(self):
        """Create a credit card is not allowed."""
        token = self.get_user_token("johndoe")
        response = self.client.post(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 405)

    def test_api_credit_card_update_without_authorization(self):
        """Update a credit card without authorization header is forbidden."""
        card = CreditCardFactory()
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            content_type="application/json",
            data={"title": "Card title updated"},
        )

        self.assertEqual(response.status_code, 401)

    def test_api_credit_card_update_with_expired_token(self):
        """Update a credit card with an expired token is forbidden."""
        user = UserFactory()
        token = self.get_user_token(
            username=user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        card = CreditCardFactory(owner=user)
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"title": "Card title updated"},
        )

        self.assertEqual(response.status_code, 401)

    def test_api_credit_card_update_with_bad_payload(self):
        """
        Update a credit card with an invalid payload should return a 400 error.
        """
        user = UserFactory()
        token = self.get_user_token(username=user.username)
        card = CreditCardFactory(owner=user)
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=[],
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {
                "non_field_errors": [
                    "Invalid data. Expected a dictionary, but got list."
                ]
            },
        )

    def test_api_credit_card_update_with_bad_user(self):
        """Update a credit card not owned by the authenticated user is forbidden."""
        user = UserFactory()
        token = self.get_user_token(username=user.username)
        card = CreditCardFactory()
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"title": "Credit card title updated!"},
        )

        self.assertEqual(response.status_code, 404)

    def test_api_credit_card_demote_credit_card_is_forbidden(self):
        """Demote a main credit card is forbidden"""
        user = UserFactory()
        token = self.get_user_token(username=user.username)
        card = CreditCardFactory(owner=user)
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"is_main": False},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data, {"__all__": ["Demote a main credit card is forbidden"]}
        )

    def test_api_credit_card_promote_credit_card(self):
        """
        Promote credit card is allowed and existing credit card should be demoted.
        """
        user = UserFactory()
        token = self.get_user_token(username=user.username)
        main_card, card = CreditCardFactory.create_batch(2, owner=user)
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"is_main": True},
        )

        self.assertEqual(response.status_code, 200)

        # - Before update state
        self.assertTrue(main_card.is_main)
        self.assertFalse(card.is_main)

        main_card.refresh_from_db()
        card.refresh_from_db()

        # - After update state
        self.assertFalse(main_card.is_main)
        self.assertTrue(card.is_main)

    def test_api_credit_card_update(self):
        """
        Update a authenticated user's credit card is allowed with a valid token.
        Only title field should be writable !
        """
        user = UserFactory()
        token = self.get_user_token(username=user.username)
        card = CreditCardFactory(owner=user)
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={
                "id": "00000000-0000-0000-0000-000000000000",
                "title": "Credit card title updated",
                "last_numbers": "0000",
                "brand": "Acme",
                "expiration_month": 12,
                "expiration_year": 2012,
            },
        )

        self.assertEqual(response.status_code, 200)

        # - Only title has been updated
        card.refresh_from_db()
        self.assertEqual(card.title, "Credit card title updated")
        self.assertNotEqual(card.id, "00000000-0000-0000-0000-000000000000")
        self.assertNotEqual(card.last_numbers, "0000")
        self.assertNotEqual(card.brand, "Acme")
        self.assertNotEqual(card.expiration_year, 2012)

    def test_api_credit_card_delete_without_authorization(self):
        """Delete credit card without authorization header is forbidden."""
        card = CreditCardFactory()
        response = self.client.delete(f"/api/v1.0/credit-cards/{card.id}/")

        self.assertEqual(response.status_code, 401)

    def test_api_credit_card_delete_with_invalid_authorization(self):
        """Delete credit card with invalid authorization header is forbidden."""
        card = CreditCardFactory()
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )

        self.assertEqual(response.status_code, 401)

    def test_api_credit_card_delete_with_expired_token(self):
        """Delete credit card with an expired token is forbidden."""
        token = self.get_user_token(
            "johndoe",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        card = CreditCardFactory()
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_api_credit_card_delete_with_bad_user(self):
        """Delete credit card not owned by the authenticated user is forbidden."""
        token = self.get_user_token("johndoe")
        card = CreditCardFactory()
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.payment.backends.dummy.DummyPaymentBackend",
            "configuration": None,
        }
    )
    def test_api_credit_card_delete(self):
        """Delete a authenticated user's credit card is allowed with a valid token."""
        user = UserFactory()
        token = self.get_user_token(user.username)
        card = CreditCardFactory(owner=user)
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 204)
