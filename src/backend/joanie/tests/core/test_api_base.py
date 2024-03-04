"""
Test suite for BaseTest class
"""

from datetime import datetime, timedelta

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class BaseAPITestTestCase(BaseAPITestCase):
    """Test suite for BaseAPITest class"""

    def test_base_api_generate_token_from_users(self):
        """If a user is passed to the method generate_token_from_user,
        the token attributes should correspond to the data of the user
        """
        user = factories.UserFactory(
            username="Sam", email="sam@fun-test.fr", language="fr-fr"
        )
        token = self.generate_token_from_user(user)
        self.assertEqual("sam@fun-test.fr", token.payload.get("email"))
        self.assertEqual("Sam", token.payload.get("username"))
        self.assertEqual("fr-fr", token.payload.get("language"))

        # expiration date is over a day from now
        self.assertGreater(
            token.payload.get("exp"), datetime.utcnow() + timedelta(days=1)
        )
