"""
Admin API Endpoints
"""
import django_filters.rest_framework
from rest_framework import authentication, permissions, viewsets

from joanie.core import filters, models, serializers


# pylint: disable=too-many-ancestors
class AdminViewSet(viewsets.ModelViewSet):
    """Admin ViewSet used as base by all admin ViewSets to restrict to admin users only."""

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser, permissions.DjangoModelPermissions]


class OrganizationViewSet(AdminViewSet):
    """
    Admin Organization ViewSet
    """

    serializer_class = serializers.AdminOrganizationSerializer
    queryset = models.Organization.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.OrganizationAdminFilterSet


class ProductViewSet(AdminViewSet):
    """
    Admin Product ViewSet
    """

    serializer_class = serializers.AdminProductSerializer
    queryset = models.Product.objects.all()
    filterset_class = filters.ProductAdminFilterSet


class CourseViewSet(AdminViewSet):
    """
    Admin Course ViewSet
    """

    serializer_class = serializers.AdminCourseSerializer
    queryset = models.Course.objects.all().prefetch_related("organizations", "products")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseAdminFilterSet


class CourseRunViewSet(AdminViewSet):
    """
    Admin CourseRun ViewSet
    """

    serializer_class = serializers.AdminCourseRunSerializer
    queryset = models.CourseRun.objects.all().select_related("course")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseRunAdminFilterSet


class CertificateDefinitionViewSet(AdminViewSet):
    """
    Admin Certificate ViewSet
    """

    serializer_class = serializers.AdminCertificateDefinitionSerializer
    queryset = models.CertificateDefinition.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CertificateDefinitionAdminFilterSet
