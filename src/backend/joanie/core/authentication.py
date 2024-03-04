"""Authentication for joanie's core app."""

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.utils.translation import get_supported_language_variant
from django.utils.translation import gettext_lazy as _

from drf_spectacular.authentication import SessionScheme, TokenScheme
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from rest_framework import authentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings


def get_user_dict(token):
    """Get user field values from token."""
    values = {
        field: token[token_field]
        for field, token_field in settings.JWT_USER_FIELDS_SYNC.items()
        if token_field in token
    }

    try:
        values["language"] = get_supported_language_variant(
            values["language"].replace("_", "-")
        )
    except LookupError:
        values["language"] = settings.LANGUAGE_CODE

    return values


class DelegatedJWTAuthentication(JWTAuthentication):
    """Override JWTAuthentication to create missing users on the fly."""

    def get_user(self, validated_token):
        """
        Return the user related to the given validated token, creating it if necessary.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as exc:
            raise InvalidToken(
                _("Token contained no recognizable user identification")
            ) from exc

        def get_or_create_and_update_user():
            user, _created = self.user_model.objects.get_or_create(
                **{api_settings.USER_ID_FIELD: user_id},
                defaults=get_user_dict(validated_token),
            )
            user.update_from_token(validated_token)
            return user

        return SimpleLazyObject(get_or_create_and_update_user)


class OpenApiJWTAuthenticationExtension(TokenScheme):
    """Extension for specifying JWT authentication schemes."""

    target_class = "joanie.core.authentication.DelegatedJWTAuthentication"
    name = "DelegatedJWTAuthentication"

    def get_security_definition(self, auto_schema):
        """Return the security definition for JWT authentication."""
        return build_bearer_security_scheme_object(
            header_name="Authorization",
            token_prefix="Bearer",  # noqa S106
        )


class SessionAuthenticationWithAuthenticateHeader(authentication.SessionAuthentication):
    """
    This class is needed, because REST Framework's default SessionAuthentication does
    never return 401's, because they cannot fill the WWW-Authenticate header with a
    valid value in the 401 response. As a result, we cannot distinguish calls that are
    not unauthorized (401 unauthorized) and calls for which the user does not have
    permission (403 forbidden).
    See https://github.com/encode/django-rest-framework/issues/5968

    We do set authenticate_header function in SessionAuthentication, so that a value
    for the WWW-Authenticate header can be retrieved and the response code is
    automatically set to 401 in case of unauthenticated requests.
    """

    def authenticate_header(self, request):
        return "Session"


class OpenApiSessionAuthenticationExtension(SessionScheme):
    """Extension for specifying session authentication schemes."""

    target_class = (
        "joanie.core.authentication.SessionAuthenticationWithAuthenticateHeader"
    )
