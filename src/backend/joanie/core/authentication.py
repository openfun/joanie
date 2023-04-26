"""Authentication for joanie's core app."""
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.utils.translation import get_supported_language_variant
from django.utils.translation import gettext_lazy as _

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
                defaults=get_user_dict(validated_token)
            )
            user.update_from_token(validated_token)
            return user

        return SimpleLazyObject(get_or_create_and_update_user)
