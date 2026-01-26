"""
Unit tests for the DelegatedJWTAuthentication backend.
"""

from unittest.mock import MagicMock, patch

from django.test import override_settings

from joanie.core import factories, models
from joanie.core.authentication import DelegatedJWTAuthentication
from joanie.tests.base import BaseAPITestCase


@override_settings(
    SIMPLE_JWT={
        "TOKEN_TYPE_CLAIM": "token_type",
    },
    JWT_USER_FIELDS_SYNC={
        "email": "email",
        "first_name": "full_name",
        "language": "language",
        "has_subscribed_to_commercial_newsletter": "has_subscribed_to_commercial_newsletter",
    },
)
@patch(
    "joanie.core.authentication.api_settings",
    MagicMock(
        USER_ID_FIELD="username",
        USER_ID_CLAIM="username",
    ),
)
class DelegatedJWTAuthenticationTestCase(BaseAPITestCase):
    """
    Unit test suite to validate the behavior of the DelegatedJWTAuthentication backend.
    """

    def test_authentication_delegated_user_unknown(self):
        """If the user is unknown, it should be created on the fly."""
        token = self.get_user_token("dave")
        token.payload.update(
            {
                "full_name": "David",
                "email": "david.bowman@hal.com",
                "language": "fr-fr",
                "has_subscribed_to_commercial_newsletter": True,
            }
        )

        auth_user = DelegatedJWTAuthentication().get_user(token)

        # The user should not be created yet
        self.assertFalse(models.User.objects.exists())

        # Now trigger the lazy wrapper evaluation
        str(auth_user)

        # The user should now have been created
        user = models.User.objects.get()
        self.assertEqual(user.email, "david.bowman@hal.com")
        self.assertEqual(user.username, "dave")
        self.assertEqual(user.first_name, "David")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.has_subscribed_to_commercial_newsletter)

    def test_authentication_delegated_user_existing(self):
        """
        If the user is existing, it should get synchronized but only when
        the user is accessed from the request.
        """
        user = factories.UserFactory(first_name="Rodolphe")
        other_user = factories.UserFactory(first_name="Rudiger")

        token = self.generate_token_from_user(user)
        token["full_name"] = "Thomas"

        auth_user = DelegatedJWTAuthentication().get_user(token)

        self.assertEqual(models.User.objects.count(), 2)

        # The user should not have been synchronized yet
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Rodolphe")

        # Now trigger the lazy wrapper evaluation
        str(auth_user)

        # The user should not have been synchronized
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Thomas")

        # The other user was left unchanged
        other_user.refresh_from_db()
        self.assertEqual(other_user.first_name, "Rudiger")


@override_settings(
    SIMPLE_JWT={
        "TOKEN_TYPE_CLAIM": "typ",
        "ISSUER": "https://keycloak/auth/realms/joanie",
        "JWK_URL": "https://keycloak/auth/realms/joanie/protocol/openid-connect/certs",
    },
    JWT_USER_FIELDS_SYNC={
        "username": "preferred_username",
        "first_name": "given_name",
        "last_name": "family_name",
        "email": "email",
        "language": "locale",
    },
)
@patch(
    "joanie.core.authentication.api_settings",
    MagicMock(
        USER_ID_FIELD="username",
        USER_ID_CLAIM="preferred_username",
    ),
)
class DelegatedJWTAuthenticationKeycloakTestCase(BaseAPITestCase):
    """
    Unit test suite to validate the behavior of the DelegatedJWTAuthentication backend.
    """

    def test_authentication_delegated_user_unknown(self):
        """If the user is unknown, it should be created on the fly."""
        token = self.get_user_token("dave")
        token.payload.update(
            {
                "preferred_username": "davy",
                "given_name": "David",
                "family_name": "Bowman",
                "email": "david.bowman@hal.com",
                "locale": "fr-fr",
            }
        )

        auth_user = DelegatedJWTAuthentication().get_user(token)

        # The user should not be created yet
        self.assertFalse(models.User.objects.exists())

        # Now trigger the lazy wrapper evaluation
        str(auth_user)

        # The user should now have been created
        user = models.User.objects.get()
        self.assertEqual(user.email, "david.bowman@hal.com")
        self.assertEqual(user.username, "davy")
        self.assertEqual(user.first_name, "David")
        self.assertEqual(user.last_name, "Bowman")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.has_subscribed_to_commercial_newsletter)

    def test_authentication_delegated_user_existing(self):
        """
        If the user is existing, it should get synchronized but only when
        the user is accessed from the request.
        """
        user = factories.UserFactory(first_name="Rodolphe")
        other_user = factories.UserFactory(first_name="Rudiger")

        token = self.generate_token_from_user(user)
        token["given_name"] = "Thomas"

        auth_user = DelegatedJWTAuthentication().get_user(token)

        self.assertEqual(models.User.objects.count(), 2)

        # The user should not have been synchronized yet
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Rodolphe")

        # Now trigger the lazy wrapper evaluation
        str(auth_user)

        # The user should not have been synchronized
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Thomas")

        # The other user was left unchanged
        other_user.refresh_from_db()
        self.assertEqual(other_user.first_name, "Rudiger")
