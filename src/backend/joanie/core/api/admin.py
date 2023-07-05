"""
Admin API Endpoints
"""
import django_filters.rest_framework
from rest_framework import authentication, permissions, viewsets

from joanie.core import filters, models, serializers


# pylint: disable=too-many-ancestors
class HasAdminPermissions(permissions.IsAdminUser, permissions.DjangoModelPermissions):
    """
    Default permissions for admin endpoints. It ensures that the user is an admin and
    has the required permissions for the model.
    """


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Admin Organization ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [HasAdminPermissions]
    serializer_class = serializers.AdminOrganizationSerializer
    queryset = models.Organization.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.OrganizationAdminFilterSet


class ProductViewSet(viewsets.ModelViewSet):
    """
    Admin Product ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [HasAdminPermissions]
    serializer_class = serializers.AdminProductSerializer
    queryset = models.Product.objects.all()
    filterset_class = filters.ProductAdminFilterSet


class CourseViewSet(viewsets.ModelViewSet):
    """
    Admin Course ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [HasAdminPermissions]
    serializer_class = serializers.AdminCourseSerializer
    queryset = models.Course.objects.all().prefetch_related("organizations", "products")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseAdminFilterSet


class CourseRunViewSet(viewsets.ModelViewSet):
    """
    Admin CourseRun ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [HasAdminPermissions]
    serializer_class = serializers.AdminCourseRunSerializer
    queryset = models.CourseRun.objects.all().select_related("course")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseRunAdminFilterSet


class CertificateDefinitionViewSet(viewsets.ModelViewSet):
    """
    Admin Certificate ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [HasAdminPermissions]
    serializer_class = serializers.AdminCertificateDefinitionSerializer
    queryset = models.CertificateDefinition.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CertificateDefinitionAdminFilterSet
