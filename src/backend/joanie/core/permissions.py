"""Permission handlers for joanie's core app."""
from abc import abstractmethod

from rest_framework import permissions

from .enums import ADMIN, OWNER


class BaseAccessPermission(permissions.BasePermission):
    """Base permission class for accesses."""

    @abstractmethod
    def get_resource(self, obj):
        """Retun the resource instance to which accesses are attached."""

    def has_permission(self, request, view):
        """Only allow authenticated users."""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check that the logged-in user is administrator of the linked resource.
        """
        if request.method == "DELETE" and obj.role == OWNER:
            return obj.user.username == request.user.username

        return (
            self.get_resource(obj)
            .accesses.filter(
                user__username=request.user.username,
                role__in=[ADMIN, OWNER],
            )
            .exists()
        )


class CourseAccessPermission(BaseAccessPermission):
    """Permissions for course accesses."""

    def get_resource(self, obj):
        """Retun the course instance to which accesses are attached."""
        return obj.course


class OrganizationAccessPermission(BaseAccessPermission):
    """Permissions for organization accesses."""

    def get_resource(self, obj):
        """Retun the organization instance to which accesses are attached."""
        return obj.organization
