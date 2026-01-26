"""
JWT tokens utilities
"""

from datetime import datetime, timedelta

from django.conf import settings

from rest_framework_simplejwt.tokens import AccessToken

from joanie.core import models
from joanie.core.authentication import KeycloakAccessToken


def generate_jwt_token_from_user(
    user: models.User, expires_at: datetime = None
) -> AccessToken | KeycloakAccessToken:
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
    if issuer := settings.SIMPLE_JWT.get("ISSUER"):
        token = KeycloakAccessToken()
        token.payload.update(
            {
                "exp": expires_at or issued_at + timedelta(days=2),
                "iat": issued_at,
                "auth_time": 1768924092,
                "jti": "c7ee46da-8127-51d1-35b1-3f07fa1a49a5",
                "iss": issuer,
                "aud": "keycloak-client",
                "sub": "095009db-b774-4e26-ab58-5e55c1474d98",
                "typ": "ID",
                "azp": "keycloak-client",
                "nonce": "1a21d63a-930b-457f-9445-0858645f77ba",
                "sid": "9f00242d-9199-80d8-178a-5f9c73968385",
                "at_hash": "SPRUypol4zCSgENoM3764g",
                "acr": "0",
                "s_hash": "YFa348xSzi5FBMi4x9w6jg",
                "email_verified": False,
                "name": user.get_full_name(),
                "preferred_username": user.username,
                "given_name": user.first_name,
                "family_name": user.last_name,
                "email": user.email,
                "locale": user.language,
            }
        )
        backend = token.get_token_backend()
        backend.algorithm = "HS256"
    else:
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
