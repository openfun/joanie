"""
Test suite for credit card API
"""
import datetime
import json
import logging

from django.test import override_settings
from django.utils import timezone

import arrow

from joanie.core import factories, models

from .base import BaseAPITestCase

CREDIT_CARD_DATA = {
    "name": "Personal",
    "card_number": "1111222233334444",
    "expiration_date": (timezone.now() + datetime.timedelta(days=400)).strftime(
        "%m/%y"
    ),
    "cryptogram": "222",
    "main": True,
}


# pylint: disable=too-many-public-methods
class CreditCardAPITestCase(BaseAPITestCase):
    """Manage user credit card API test case"""

    def test_get_credit_cards_without_authorization(self):
        """Get user credit cards not allowed without HTTP AUTH"""
        # Try to get credit cards without Authorization
        response = self.client.get("/api/credit-cards/")
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_get_credit_cards_with_bad_token(self):
        """Get user credit cards not allowed with bad user token"""
        # Try to get credit cards with bad token
        response = self.client.get(
            "/api/credit-cards/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_get_credit_cards_with_expired_token(self):
        """Get user credit cards not allowed with user token expired"""
        # Try to get credit cards with expired token
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/credit-cards/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_get_credit_cards_for_new_user(self):
        """If we try to get credit cards for a user not in db, we create a new user first"""
        username = "panoramix"
        token = self.get_user_token(username)
        response = self.client.get(
            "/api/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        credit_cards_data = response.data
        self.assertEqual(len(credit_cards_data), 0)
        self.assertEqual(models.User.objects.get(username=username).username, username)

    def test_get_credit_cards(self):
        """Get credit cards for a user in db with two credit cards linked to him"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        credit_card1 = factories.CreditCardFactory.create(owner=user, name="Personal")
        credit_card2 = factories.CreditCardFactory.create(
            owner=user, name="Professional"
        )
        response = self.client.get(
            "/api/credit-cards/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)

        credit_cards_data = response.data
        self.assertEqual(len(credit_cards_data), 2)
        self.assertEqual(credit_cards_data[0]["name"], "Personal")
        self.assertEqual(credit_cards_data[0]["id"], credit_card1.uid)
        self.assertEqual(
            credit_cards_data[0]["last_numbers"], credit_card1.last_numbers
        )
        self.assertEqual(credit_cards_data[1]["name"], "Professional")
        self.assertEqual(credit_cards_data[1]["id"], credit_card2.uid)
        self.assertEqual(
            credit_cards_data[1]["last_numbers"], credit_card2.last_numbers
        )
        self.assertEqual(
            credit_cards_data[1]["expiration_date"],
            credit_card2.expiration_date.strftime("%m/%y"),
        )

    def test_create_credit_card_without_authorization(self):
        """Create user credit card not allowed without HTTP AUTH"""
        # Try to create credit card without Authorization
        response = self.client.post(
            "/api/credit-cards/",
            data=CREDIT_CARD_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_update_credit_card_without_authorization(self):
        """Update user credit_card not allowed without HTTP AUTH"""
        # Try to update credit card without Authorization
        user = factories.UserFactory()
        credit_card = factories.CreditCardFactory.create(owner=user)
        response = self.client.put(
            f"/api/credit-cards/{credit_card.uid}",
            data=CREDIT_CARD_DATA,
            follow=True,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_create_credit_card_with_bad_token(self):
        """Create credit card not allowed with bad user token"""
        # Try to create credit card with bad token
        response = self.client.post(
            "/api/credit-cards/",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=CREDIT_CARD_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_update_credit_card_with_bad_token(self):
        """Update credit card not allowed with bad user token"""
        # Try to update credit card with bad token
        user = factories.UserFactory()
        credit_card = factories.CreditCardFactory.create(owner=user)
        response = self.client.put(
            f"/api/credit-cards/{credit_card.uid}",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=CREDIT_CARD_DATA,
            follow=True,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_create_credit_card_with_expired_token(self):
        """Create user credit card not allowed with user token expired"""
        # Try to create credit card with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.post(
            "/api/credit-cards/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=CREDIT_CARD_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_update_credit_card_with_expired_token(self):
        """Update user credit card not allowed with user token expired"""
        # Try to update credit card with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        credit_card = factories.CreditCardFactory.create(owner=user)
        response = self.client.put(
            f"/api/credit-cards/{credit_card.uid}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=CREDIT_CARD_DATA,
            follow=True,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_create_credit_card_with_bad_data(self):
        """Create user credit card with valid token but bad data"""
        username = "panoramix"
        token = self.get_user_token(username)

        fields_to_check = [
            ("card_number", "nawak", "Enter a valid value (16 digits)"),
            ("cryptogram", "nawak", "Enter a valid value (3 digits)"),
            ("expiration_date", "nawak", "Enter a valid value 'month/year'"),
        ]
        for field, bad_value, error_message in fields_to_check:
            bad_data = CREDIT_CARD_DATA.copy()
            bad_data[field] = bad_value
            response = self.client.post(
                "/api/credit-cards/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=bad_data,
            )
            self.assertEqual(response.status_code, 400)
            content = json.loads(response.content)
            self.assertEqual(content, {"errors": {field: [error_message]}})
            self.assertFalse(models.User.objects.exists())
            self.assertFalse(models.CreditCard.objects.exists())

    def test_update_credit_card_with_bad_data(self):
        """Update user credit card with valid token but bad data"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        credit_card = factories.CreditCardFactory.create(owner=user)

        # check bad request returned if credit card id is missing
        response = self.client.put(
            "/api/credit-cards/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=CREDIT_CARD_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        bad_data = CREDIT_CARD_DATA.copy()
        del bad_data["name"]
        response = self.client.put(
            f"/api/credit-cards/{credit_card.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"errors": {"name": ["This field is required."]}})

    def test_update_credit_card_with_bad_user(self):
        """User token has to match with owner of credit card to update"""
        # create a credit card for a user
        credit_card = factories.CreditCardFactory()
        # now use a token for an other user to update credit card
        token = self.get_user_token("panoramix")
        response = self.client.put(
            f"/api/credit-cards/{credit_card.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=CREDIT_CARD_DATA,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
    )
    def test_create_update_credit_card(self):
        """Create/Update user credit card with valid token and data"""
        username = "panoramix"
        token = self.get_user_token(username)

        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            response = self.client.post(
                "/api/credit-cards/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=CREDIT_CARD_DATA,
                content_type="application/json",
            )
            self.assertTrue("successfully registered" in logs.output[0])

        # panoramix was a unknown user, so a new user was created
        owner = models.User.objects.get()
        self.assertEqual(owner.username, username)

        # new credit card was created for user panoramix
        credit_card = models.CreditCard.objects.get()
        self.assertEqual(credit_card.owner, owner)
        self.assertEqual(credit_card.name, "Personal")

        self.assertEqual(
            json.loads(response.content),
            {
                "id": str(credit_card.uid),
                "name": credit_card.name,
                "last_numbers": CREDIT_CARD_DATA["card_number"][-4:],
                "expiration_date": CREDIT_CARD_DATA["expiration_date"],
                "main": CREDIT_CARD_DATA["main"],
            },
        )
        self.assertEqual(response.status_code, 201)

        # finally update name
        data = CREDIT_CARD_DATA.copy()
        data["name"] = "Professional"
        data["main"] = False
        response = self.client.put(
            f"/api/credit-cards/{credit_card.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.CreditCard.objects.count(), 1)
        credit_card = models.CreditCard.objects.get()
        self.assertEqual(credit_card.name, "Professional")
        self.assertEqual(credit_card.owner, owner)
        self.assertEqual(
            json.loads(response.content),
            {
                "id": str(credit_card.uid),
                "name": "Professional",
                "last_numbers": CREDIT_CARD_DATA["card_number"][-4:],
                "expiration_date": CREDIT_CARD_DATA["expiration_date"],
                "main": False,
            },
        )

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.failing.FailingBackend"
    )
    def test_create_credit_card_failing_service(self):
        """Try to create user credit card but service backend failed"""
        username = "panoramix"
        token = self.get_user_token(username)

        with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
            response = self.client.post(
                "/api/credit-cards/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=CREDIT_CARD_DATA,
                content_type="application/json",
            )
            # registration failure log
            self.assertTrue(
                f"Registration credit card ****{CREDIT_CARD_DATA['card_number'][-4:]} failed"
                in logs.output[0]
            )
            self.assertEqual(response.status_code, 400)
            self.assertTrue("Service failed" in json.loads(response.content)["errors"])

            # panoramix was a unknown user, so a new user was created
            owner = models.User.objects.get()
            self.assertEqual(owner.username, username)

            # no credit card was created for user panoramix
            self.assertFalse(models.CreditCard.objects.exists())

    def test_delete_without_authorization(self):
        """Delete credit card is not allowed without authorization"""
        user = factories.UserFactory()
        credit_card = factories.CreditCardFactory.create(owner=user)
        response = self.client.delete(
            f"/api/credit-cards/{credit_card.uid}/",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_with_bad_authorization(self):
        """Delete credit card is not allowed with bad authorization"""
        user = factories.UserFactory()
        credit_card = factories.CreditCardFactory.create(owner=user)
        response = self.client.delete(
            f"/api/credit-cards/{credit_card.uid}/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_with_expired_token(self):
        """Delete credit card is not allowed with expired token"""
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        credit_card = factories.CreditCardFactory.create(owner=user)
        response = self.client.delete(
            f"/api/credit-cards/{credit_card.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_credit_card_with_bad_user(self):
        """User token has to match with owner of credit card to delete"""
        # create an credit card for a user
        credit_card = factories.CreditCardFactory()
        # now use a token for an other user to update credit card
        token = self.get_user_token("panoramix")
        response = self.client.delete(
            f"/api/credit-cards/{credit_card.uid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(
        JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
    )
    def test_delete_credit_card(self):
        """Delete credit card is allowed with valid token"""
        username = "panoramix"
        token = self.get_user_token(username)

        # first register a credit card
        self.client.post(
            "/api/credit-cards/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=CREDIT_CARD_DATA,
            content_type="application/json",
        )

        # then delete credit card
        credit_card = models.CreditCard.objects.get()
        with self.assertLogs(logging.getLogger(), level="INFO") as logs:
            response = self.client.delete(
                f"/api/credit-cards/{credit_card.uid}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, 204)
            self.assertFalse(models.CreditCard.objects.exists())
            self.assertTrue("succeeded" in logs.output[0])

    def test_delete_credit_card_failing_service(self):
        """Try to delete credit card but payment service failed"""
        username = "panoramix"
        token = self.get_user_token(username)

        # first register a credit card
        with override_settings(
            JOANIE_PAYMENT_BACKEND="joanie.payment.backends.dummy.DummyBackend"
        ):
            self.client.post(
                "/api/credit-cards/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=CREDIT_CARD_DATA,
                content_type="application/json",
            )
        credit_card = models.CreditCard.objects.get()

        # then try to delete credit card with failing service
        with self.assertLogs(logging.getLogger(), level="ERROR") as logs:
            with override_settings(
                JOANIE_PAYMENT_BACKEND="joanie.payment.backends.failing.FailingBackend"
            ):
                response = self.client.delete(
                    f"/api/credit-cards/{credit_card.uid}/",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )
                self.assertEqual(response.status_code, 400)
                self.assertTrue(
                    "Service failed" in json.loads(response.content)["errors"]
                )
                self.assertTrue(models.CreditCard.objects.exists())
                self.assertTrue("failed with error" in logs.output[0])
