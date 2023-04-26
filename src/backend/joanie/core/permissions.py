"""Permission handlers for joanie's core app."""
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
        abilities = obj.get_abilities(
            user=request.user, auth=getattr(request, "auth", None)
        )
        return abilities.get(request.method.lower(), False)
