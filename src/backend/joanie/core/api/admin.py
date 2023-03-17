"""
Admin API Endpoints
"""
from rest_framework import authentication, permissions, viewsets

from joanie.core import models, serializers


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


class ProductViewSet(AdminViewSet):
    """
    Admin Product ViewSet
    """

    serializer_class = serializers.AdminProductSerializer
    queryset = models.Product.objects.all()


class CourseViewSet(AdminViewSet):
    """
    Admin Course ViewSet
    """

    serializer_class = serializers.AdminCourseSerializer
    queryset = models.Course.objects.all().prefetch_related("organizations", "products")


class CourseRunViewSet(AdminViewSet):
    """
    Admin CourseRun ViewSet
    """

    serializer_class = serializers.AdminCourseRunSerializer
    queryset = models.CourseRun.objects.all().select_related("course")


class CertificateDefinitionViewSet(AdminViewSet):
    """
    Admin Certificate ViewSet
    """

    serializer_class = serializers.AdminCertificateDefinitionSerializer
    queryset = models.CertificateDefinition.objects.all()
