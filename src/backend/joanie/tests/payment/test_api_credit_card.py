"""
Test suite for the Credit Card API
"""

import json
from decimal import Decimal as D
from http import HTTPStatus
from unittest import mock

from django.test.utils import override_settings
from django.urls import reverse

import arrow
from rest_framework.pagination import PageNumberPagination
from rest_framework.test import APIRequestFactory

from joanie.core.enums import ORDER_STATE_PENDING
from joanie.core.factories import OrderGeneratorFactory, UserFactory
from joanie.core.models import User
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.factories import CreditCardFactory
from joanie.payment.models import CreditCard
from joanie.tests.base import BaseAPITestCase


# pylint: disable=too-many-public-methods
class CreditCardAPITestCase(BaseAPITestCase):
    """Manage user's credit cards API test cases"""

    def test_api_credit_card_list_without_authorization(self):
        """List credit cards without authorization header is forbidden."""
        response = self.client.get("/api/v1.0/credit-cards/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.data, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_credit_card_list_with_bad_token(self):
        """List credit cards with bad token is forbidden."""
        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION="Bearer invalid_token"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.data["code"], "token_not_valid")

    def test_api_credit_card_list_with_expired_token(self):
        """List credit cards with an expired token is forbidden."""
        token = self.get_user_token(
            "johndoe",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.data["code"], "token_not_valid")

    def test_api_credit_card_list_for_new_user(self):
        """
        List credit cards of a non-existing user is allowed but create an user first.
        """
        username = "johndoe"
        self.assertFalse(User.objects.filter(username=username).exists())
        token = self.get_user_token(username)
        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(), {"count": 0, "next": None, "previous": None, "results": []}
        )
        self.assertTrue(User.objects.filter(username=username).exists())

    def test_api_credit_card_list(self):
        """
        Authenticated user should be able to list all his credit cards
        with the active payment backend.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        # Create 2 cards for the user with the active payment_provider name
        cards = CreditCardFactory.create_batch(2, owners=[user])
        # Create 1 card for the user with another payment_provider name
        CreditCardFactory(owners=[user], payment_provider="lyra")

        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        results = content.pop("results")
        cards.sort(key=lambda card: card.created_on, reverse=True)
        cards.sort(key=lambda card: card.is_main, reverse=True)
        self.assertEqual(
            [result["id"] for result in results], [str(card.id) for card in cards]
        )
        # We should find 2 credit cards in count out of 3 for the user
        self.assertEqual(
            content,
            {
                "count": 2,
                "next": None,
                "previous": None,
            },
        )

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_credit_card_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""
        user = UserFactory()
        token = self.generate_token_from_user(user)
        cards = CreditCardFactory.create_batch(3, owners=[user])
        card_ids = [str(card.id) for card in cards]

        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"], "http://testserver/api/v1.0/credit-cards/"
        )

        self.assertEqual(len(content["results"]), 1)
        card_ids.remove(content["results"][0]["id"])
        self.assertEqual(card_ids, [])

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_credit_card_list_sorted_by_is_main_then_created_on(
        self, _mock_page_size
    ):
        """
        List credit cards should always return first the main credit card then
        all others sorted by created_on desc.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        cards = CreditCardFactory.create_batch(3, owners=[user])
        cards.sort(key=lambda card: card.created_on, reverse=True)
        cards.sort(key=lambda card: card.is_main, reverse=True)
        sorted_card_ids = [str(card.id) for card in cards]

        response = self.client.get(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        results_ids = [result["id"] for result in content["results"]]
        self.assertListEqual(results_ids, sorted_card_ids[:2])
        self.assertEqual(content["results"][0]["is_main"], True)

        # Get page 2
        response = self.client.get(
            "/api/v1.0/credit-cards/?page=2", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()

        self.assertEqual(content["count"], 3)
        results_ids = [result["id"] for result in content["results"]]
        self.assertListEqual(results_ids, sorted_card_ids[2:])

    def test_api_credit_card_get(self):
        """Retrieve authenticated user's credit card by its id is allowed."""
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory(owners=[user])

        response = self.client.get(
            f"/api/v1.0/credit-cards/{card.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

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

    def test_api_credit_card_get_non_existing(self):
        """Retrieve a non-existing credit card should return a 404."""
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory.build(owners=[user])

        response = self.client.get(
            f"/api/v1.0/credit-cards/{card.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_credit_card_get_not_owned(self):
        """
        Retrieve credit card don't owned by the authenticated user should return a 404.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory()

        response = self.client.get(
            f"/api/v1.0/credit-cards/{card.id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_credit_card_create_is_not_allowed(self):
        """Create a credit card is not allowed."""
        token = self.get_user_token("johndoe")
        response = self.client.post(
            "/api/v1.0/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_credit_card_update_without_authorization(self):
        """Update a credit card without authorization header is forbidden."""
        card = CreditCardFactory()
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            content_type="application/json",
            data={"title": "Card title updated"},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_credit_card_update_with_expired_token(self):
        """Update a credit card with an expired token is forbidden."""
        user = UserFactory()
        token = self.generate_token_from_user(
            user,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        card = CreditCardFactory(owners=[user])
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"title": "Card title updated"},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_credit_card_update_with_bad_payload(self):
        """
        Update a credit card with an invalid payload should return a 400 error.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory(owners=[user])
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=[],
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
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
        token = self.generate_token_from_user(user)
        card = CreditCardFactory()
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"title": "Credit card title updated!"},
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_credit_card_demote_credit_card_is_forbidden(self):
        """Demote a main credit card is forbidden"""
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory(owners=[user])
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"is_main": False},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.data, {"__all__": ["Demote a main credit card is forbidden"]}
        )

    def test_api_credit_card_promote_credit_card(self):
        """
        Promote credit card is allowed and existing credit card should be demoted.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        main_card, card = CreditCardFactory.create_batch(2, owners=[user])
        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"is_main": True},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # - Before update state
        self.assertTrue(main_card.is_main)
        self.assertFalse(card.is_main)

        main_card.refresh_from_db()
        card.refresh_from_db()

        # - After update state
        self.assertFalse(main_card.is_main)
        self.assertTrue(card.is_main)

    def test_api_credit_card_promote_to_is_main_when_multiple_owners(self):
        """
        Promote credit card is allowed and existing credit card should be demoted.
        When there are multiple owners, every owner will see the same card be the
        main one if one user decides to promote it.
        """
        [user_1, user_2, user_3] = UserFactory.create_batch(3)
        token = self.generate_token_from_user(user_1)
        main_card, card = CreditCardFactory.create_batch(
            2, owners=[user_1, user_2, user_3]
        )

        # - Before update state
        self.assertTrue(main_card.is_main)
        self.assertFalse(card.is_main)

        response = self.client.put(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={"is_main": True},
        )

        main_card.refresh_from_db()
        card.refresh_from_db()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        # - After update state
        self.assertFalse(main_card.is_main)
        self.assertTrue(card.is_main)

        # They all own that same card, all have the same main one
        self.assertTrue(user_1.payment_cards.get(is_main=True), card)
        self.assertTrue(user_2.payment_cards.get(is_main=True), card)
        self.assertTrue(user_3.payment_cards.get(is_main=True), card)

    def test_api_credit_card_update(self):
        """
        Update an authenticated user's credit card is allowed with a valid token.
        Only title field should be writable !
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory(owners=[user])
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

        self.assertEqual(response.status_code, HTTPStatus.OK)

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

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_credit_card_delete_with_invalid_authorization(self):
        """Delete credit card with invalid authorization header is forbidden."""
        card = CreditCardFactory()
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_credit_card_delete_with_bad_user(self):
        """Delete credit card not owned by the authenticated user is forbidden."""
        token = self.get_user_token("johndoe")
        card = CreditCardFactory()
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.payment.backends.dummy.DummyPaymentBackend",
            "configuration": None,
        }
    )
    def test_api_credit_card_delete(self):
        """Delete a authenticated user's credit card is allowed with a valid token."""
        user = UserFactory()
        token = self.generate_token_from_user(user)
        card = CreditCardFactory(owners=[user])
        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_api_credit_card_delete_but_credit_card_is_shared_by_3_users(self):
        """
        When an authenticated user decides to delete a shared credit card, it will remove
        his relation to the credit card if he does not have any pending payment on his orders.
        This action will not delete the credit card for the 2 other owners.
        For example, if user_2 attempts to delete the credit card on his side and he still
        has pending payment on an order, he will be blocked.
        """
        [user_1, user_2, user_3] = UserFactory.create_batch(3)
        card = CreditCardFactory(owners=[user_1, user_2, user_3])

        self.assertEqual(user_1.payment_cards.count(), 1)
        self.assertEqual(card.ownerships.filter(owner=user_1).count(), 1)
        self.assertEqual(user_2.payment_cards.count(), 1)
        self.assertEqual(card.ownerships.filter(owner=user_2).count(), 1)
        self.assertEqual(user_3.payment_cards.count(), 1)
        self.assertEqual(card.ownerships.filter(owner=user_3).count(), 1)

        token = self.generate_token_from_user(user_1)

        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertNotIn(user_1, card.owners.all())
        self.assertEqual(user_1.payment_cards.count(), 0)
        self.assertEqual(card.ownerships.filter(owner=user_1).count(), 0)
        self.assertEqual(user_2.payment_cards.count(), 1)
        self.assertEqual(card.ownerships.filter(owner=user_2).count(), 1)
        self.assertEqual(user_3.payment_cards.count(), 1)
        self.assertEqual(card.ownerships.filter(owner=user_3).count(), 1)

        # Create order with ongoing payments for user_2
        OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            owner=user_2,
            product__price=D("123.45"),
            credit_card=card,
        )
        token_2 = self.generate_token_from_user(user_2)

        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token_2}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertEqual(
            response.json(),
            {
                "details": "Cannot delete the credit card, there are still pending "
                f"payments for this credit card {card.id}"
            },
        )
        self.assertIn(user_2, card.owners.all())

    def test_api_credit_card_delete_when_pending_payment_on_order_is_forbidden(self):
        """
        When an authenticated user decides to delete a credit card and he still has pending
        payments on orders, it should not let him delete it.
        """
        owner = UserFactory()
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            owner=owner,
            product__price=D("123.45"),
            credit_card__initial_issuer_transaction_identifier="1",
        )
        card = order.credit_card
        token = self.generate_token_from_user(owner)

        response = self.client.delete(
            f"/api/v1.0/credit-cards/{card.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertEqual(
            response.json(),
            {
                "details": "Cannot delete the credit card, there are still pending "
                f"payments for this credit card {card.id}"
            },
        )

    def test_api_credit_card_tokenize_card_anonymous(self):
        """
        Anonymous user should not be able to tokenize a credit card
        """
        response = self.client.post("/api/v1.0/credit-cards/tokenize-card/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_credit_card_tokenize_card_get_method_not_allowed(self):
        """
        Authenticated user should not be able to GET method to tokenize his credit card
        """
        user = UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_credit_card_tokenize_card_put_method_not_allowed(self):
        """
        Authenticated user should not be able to PUT method to update a tokenize credit card
        """
        user = UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.put(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_credit_card_tokenize_card_patch_method_not_allowed(self):
        """
        Authenticated user should not be able to PATCH method to partially update tokenized
        credit card
        """
        user = UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.patch(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_credit_card_tokenize_card_delete_method_not_allowed(self):
        """
        Authenticated user should not be able to DELETE method to tokenize his credit card
        """
        user = UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.payment.backends.dummy.DummyPaymentBackend",
            "configuration": None,
        }
    )
    def test_api_credit_card_tokenize_card(self):
        """
        Authenticated user should be able to tokenize a credit card.
        """
        user = UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.post(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user.id),
                "card_token": f"card_{user.id}",
            },
        )

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.payment.backends.dummy.DummyPaymentBackend",
            "configuration": None,
        }
    )
    def test_api_credit_card_tokenize_same_credit_card_with_another_user_adds_new_entry_of_owners(
        self,
    ):
        """
        Test when a second user wants to tokenize a credit card that already exists in the
        database, he will be added to the relation into the `owners` field of that card.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()
        [user_1, user_2] = UserFactory.create_batch(2)
        token = self.get_user_token(user_1.username)

        response = self.client.post(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Notify that a card has been tokenized for a user
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user_1.id),
                "card_token": "card_dummy_test_token",
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)

        self.assertEqual(user_1.payment_cards.count(), 1)
        credit_card = CreditCard.objects.get(token="card_dummy_test_token")
        self.assertEqual(credit_card.ownerships.filter(owner=user_1).count(), 1)
        # Now the second user wants to add that same card,
        # only 1 card should exists, and both users are owners on that one.
        token = self.get_user_token(user_2.username)

        response = self.client.post(
            "/api/v1.0/credit-cards/tokenize-card/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Notify that a card has been tokenized for a user
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user_2.id),
                "card_token": "card_dummy_test_token",
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        self.assertEqual(CreditCard.objects.count(), 1)
        self.assertEqual(credit_card.owners.count(), 2)
        self.assertEqual(credit_card.ownerships.filter(owner=user_2).count(), 1)
        self.assertIn(user_1, credit_card.owners.all())
        self.assertIn(user_2, credit_card.owners.all())
