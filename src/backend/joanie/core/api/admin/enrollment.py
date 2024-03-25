"""
Admin API Enrollment Endpoints
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    mixins,
    permissions,
    viewsets,
)
from rest_framework.filters import OrderingFilter

from joanie.core import filters, models, serializers
from joanie.core.api.base import SerializerPerActionMixin
from joanie.core.authentication import SessionAuthenticationWithAuthenticateHeader


# pylint: disable=too-many-ancestors
class EnrollmentViewSet(
    SerializerPerActionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Admin Enrollment ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_classes = {
        "list": serializers.AdminEnrollmentLightSerializer,
    }
    default_serializer_class = serializers.AdminEnrollmentSerializer
    queryset = models.Enrollment.objects.all().select_related(
        "course_run", "course_run__course", "user", "certificate"
    )
    filterset_class = filters.EnrollmentAdminFilterSet
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_on"]
