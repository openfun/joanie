"""
Common base API test case
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import translation

from rest_framework_simplejwt.tokens import AccessToken


class BaseAPITestCase(TestCase):
    """Base API test case"""

    def setUp(self):
        """
        We are testing in english
        """
        super().setUp()
        translation.activate("en-us")

    @staticmethod
    def get_user_token(username, expires_at=None):
        """
        Generate a jwt token used to authenticate a user

        Args:
            username: str, username to encode
            expires_at: datetime.datetime, time after which the token should expire.

        Returns:
            token, the jwt token generated as it should
        """
        issued_at = datetime.utcnow()
        token = AccessToken()
        token.payload.update(
            {
                "email": f"{username}@funmooc.fr",
                "exp": expires_at or issued_at + timedelta(days=2),
                "iat": issued_at,
                "language": settings.LANGUAGE_CODE,
                "username": username,
            }
        )
        return token

    @staticmethod
    def generate_token_from_user(user, expires_at=None):
        """
        Generate a jwt token used to authenticate a user from a user registered in
        the database

        Args:
            user: User
            expires_at: datetime.datetime, time after which the token should expire.

        Returns:
            token, the jwt token generated as it should
        """
        issued_at = datetime.utcnow()
        token = AccessToken()
        token.payload.update(
            {
                "email": user.email,
                "exp": expires_at or issued_at + timedelta(days=2),
                "iat": issued_at,
                "language": user.language,
                "username": user.username,
            }
        )
        return token
