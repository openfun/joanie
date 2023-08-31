"""
Admin API Endpoints
"""
import django_filters.rest_framework
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from joanie.core import filters, models, serializers
from joanie.core.authentication import SessionAuthenticationWithAuthenticateHeader


# pylint: disable=too-many-ancestors
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Admin Organization ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
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

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminProductSerializer
    serializer_action_classes = {"list": serializers.AdminProductLightSerializer}
    queryset = models.Product.objects.all()
    filterset_class = filters.ProductAdminFilterSet

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]
        return self.serializer_class


class CourseViewSet(viewsets.ModelViewSet):
    """
    Admin Course ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
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

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCourseRunSerializer
    queryset = models.CourseRun.objects.all().select_related("course")
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CourseRunAdminFilterSet

    def get_queryset(self):
        """
        Return CourseRun linked to specified course if an id is given or
        all CourseRuns
        """
        queryset = super().get_queryset()
        course_id = self.kwargs.get("course_id")

        if course_id:
            queryset = queryset.filter(course=course_id)

        return queryset


class CertificateDefinitionViewSet(viewsets.ModelViewSet):
    """
    Admin Certificate ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCertificateDefinitionSerializer
    queryset = models.CertificateDefinition.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = filters.CertificateDefinitionAdminFilterSet


class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Admin User ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
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

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
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

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
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


class TargetCoursesViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Write only Product's TargetCourse ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminProductTargetCourseRelationSerializer
    queryset = models.ProductTargetCourseRelation.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Parse and create the ProductTargetCourseRelation
        """
        data = request.data
        data["product"] = kwargs.get("product_id")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        course_runs = serializer.validated_data.pop("course_runs", [])
        relation = models.ProductTargetCourseRelation(**serializer.validated_data)
        relation.save()
        for course_run in course_runs:
            relation.course_runs.add(course_run)
        response = self.get_serializer(relation)
        return Response(response.data, status=201)
