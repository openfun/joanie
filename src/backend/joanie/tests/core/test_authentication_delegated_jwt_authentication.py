"""
Unit tests for the DelegatedJWTAuthentication backend.
"""

from joanie.core import factories, models
from joanie.core.authentication import DelegatedJWTAuthentication
from joanie.tests.base import BaseAPITestCase


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
