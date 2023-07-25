"""
Admin API Endpoints
"""
import django_filters.rest_framework
from rest_framework import authentication, mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from joanie.core import filters, models, serializers


# pylint: disable=too-many-ancestors
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Admin Organization ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminOrganizationSerializer
    queryset = models.Organization.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.OrganizationAdminFilterSet

    def get_serializer_class(self):
        """
        Return the serializer class to use depending on the action.
        """
        if self.action == "list":
            return serializers.AdminOrganizationLightSerializer
        return self.serializer_class


class ProductViewSet(viewsets.ModelViewSet):
    """
    Admin Product ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminProductSerializer
    queryset = models.Product.objects.all()
    filterset_class = filters.ProductAdminFilterSet


class CourseViewSet(viewsets.ModelViewSet):
    """
    Admin Course ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCourseSerializer
    queryset = models.Course.objects.all().prefetch_related("organizations", "products")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseAdminFilterSet

    def get_serializer_class(self):
        """
        Return the serializer class to use depending on the action.
        """
        if self.action == "list":
            return serializers.AdminCourseLightSerializer
        return self.serializer_class


class CourseRunViewSet(viewsets.ModelViewSet):
    """
    Admin CourseRun ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCourseRunSerializer
    queryset = models.CourseRun.objects.all().select_related("course")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseRunAdminFilterSet


class CertificateDefinitionViewSet(viewsets.ModelViewSet):
    """
    Admin Certificate ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCertificateDefinitionSerializer
    queryset = models.CertificateDefinition.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CertificateDefinitionAdminFilterSet


class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Admin User ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminUserSerializer
    me_serializer_class = serializers.AdminUserCompleteSerializer
    queryset = models.User.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.UserAdminFilterSet

    def get_queryset(self):
        """
        Only return users if a query is provided to filter them.
        """
        query = self.request.query_params.get("query", None)

        if not query:
            return models.User.objects.none()

        return super().get_queryset()

    @action(
        detail=False,
        methods=["get"],
        url_name="me",
        url_path="me",
        permission_classes=[
            permissions.IsAdminUser & permissions.DjangoModelPermissions
        ],
    )
    def get_me(self, request):
        """
        Return information on currently logged user
        """
        context = {"request": request}
        return Response(self.me_serializer_class(request.user, context=context).data)


class CourseAccessViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Write only Course Access ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCourseAccessSerializer
    queryset = models.CourseAccess.objects.all().select_related("user")

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        context["course_id"] = self.kwargs["course_id"]
        return context


class OrganizationAccessViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Write only Organization Access ViewSet
    """

    authentication_classes = [authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminOrganizationAccessSerializer
    queryset = models.OrganizationAccess.objects.all().select_related("user")

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        context["organization_id"] = self.kwargs["organization_id"]
        return context
