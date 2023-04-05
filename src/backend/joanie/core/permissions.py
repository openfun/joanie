"""Permission handlers for joanie's core app."""
from rest_framework import permissions

from .enums import ADMIN, OWNER


class OrganizationAccessPermission(permissions.BasePermission):
    """Permissions for organization accesses."""

    def has_permission(self, request, view):
        """Only allow authenticated users."""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check that the logged-in user is administrator of the linked organization.
        """
        if request.method == "DELETE" and obj.role == OWNER:
            return obj.user.username == request.user.username

        return obj.organization.accesses.filter(
            user__username=request.user.username,
            role__in=[ADMIN, OWNER],
        ).exists()
