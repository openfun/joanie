"""
JWT tokens utilities
"""

from datetime import datetime, timedelta

from rest_framework_simplejwt.tokens import AccessToken

from joanie.core import models


def generate_jwt_token_from_user(
    user: models.User, expires_at: datetime = None
) -> AccessToken:
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
            "full_name": user.get_full_name(),
        }
    )
    return token
