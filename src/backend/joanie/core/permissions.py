"""Permission handlers for joanie's core app."""

from django.conf import settings

from rest_framework import permissions


class IsAuthenticated(permissions.BasePermission):
    """
    Allows access only to authenticated users. Alternative method checking the presence
    of the auth token to avoid hitting the database.
    """

    def has_permission(self, request, view):
        return bool(request.auth) if request.auth else request.user.is_authenticated


class AccessPermission(IsAuthenticated):
    """Permission class for access objects."""

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)
        return abilities.get(request.method.lower(), False)


class CanSignOrganizationContracts(IsAuthenticated):
    """
    Check if the authenticated user is allowed to sign contracts of an organization.
    """

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)
        return abilities.get("sign_contracts", False)


class CanDownloadQuoteOrganization(IsAuthenticated):
    """
    Check if the authenticated user is allowed to download the quote of an organization
    from a batch order.
    """

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)
        return abilities.get("download_quote", False)


class CanConfirmQuoteOrganization(IsAuthenticated):
    """
    Check if the authenticated user is allowed to confirm the quote of an organization
    from a batch order.
    """

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)
        return abilities.get("confirm_quote", False)


class CanConfirmOrganizationBankTransfer(IsAuthenticated):
    """
    Check if the authenticated user is allowed to confirm the bank transfer of a batch order
    for an organization.
    """

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)
        return abilities.get("confirm_bank_transfer", False)


class HasAPIKey(permissions.BasePermission):
    """Permission class to grant access to our remote endpoints API."""

    def has_permission(self, request, view):
        """
        Check if a valid authorization token is present in the request headers.

        This method verifies whether the token is included in the 'Authorization' header
        and follows the 'Bearer' scheme. It then checks if the token exists in the list
        of authorized tokens specified by `JOANIE_AUTHORIZED_API_TOKENS` variable in settings.
        """
        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            return False

        try:
            scheme_prefix, token = authorization_header.split(maxsplit=1)
        except ValueError:
            return False

        if scheme_prefix != "Bearer":
            return False

        return token in settings.JOANIE_AUTHORIZED_API_TOKENS
