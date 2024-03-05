"""
Admin API Endpoints
"""

from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.http import JsonResponse

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from joanie.core import filters, models, serializers
from joanie.core.api.base import NestedGenericViewSet, SerializerPerActionMixin
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
    filterset_class = filters.CertificateDefinitionAdminFilterSet


class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Admin User ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminUserSerializer
    me_serializer_class = serializers.AdminUserCompleteSerializer
    queryset = models.User.objects.all().order_by("username")
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
        serializer = self.get_serializer(data=data)
        data["product"] = kwargs.get("product_id")
        # Data has to be fixed before validation because the front-end
        # may set "course_runs": "" which is not accepted by the serializer
        if not data.get("course_runs", None):
            data["course_runs"] = []
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
        course_runs = serializer.validated_data.pop("course_runs", [])
        relation = models.ProductTargetCourseRelation(**serializer.validated_data)
        relation.save()
        for course_run in course_runs:
            relation.course_runs.add(course_run)
        response = self.get_serializer(relation)
        return Response(response.data, status=HTTPStatus.CREATED)

    def partial_update(self, request, *args, **kwargs):
        """
        Parse and patch the ProductTargetCourseRelation
        """
        data = request.data
        data["product"] = kwargs.get("product_id")
        # Data has to be fixed before validation because the front-end
        # may set "course_runs": "" which is not accepted by the serializer
        if data.get("course_runs", None) == "":
            data["course_runs"] = []
        relation = self.queryset.get(product=data["product"], course=kwargs["pk"])
        serializer = self.get_serializer(relation, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
        course_runs = serializer.validated_data.pop("course_runs", None)
        models.ProductTargetCourseRelation.objects.filter(pk=relation.id).update(
            **serializer.validated_data
        )
        relation.refresh_from_db()
        if course_runs is not None:
            relation.course_runs.clear()
            for course_run in course_runs:
                relation.course_runs.add(course_run)
        response = self.get_serializer(relation)
        return Response(response.data, status=HTTPStatus.CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Delete the relation between product_id and course_id
        """
        product_id = kwargs.get("product_id")
        course_id = kwargs["pk"]
        self.queryset.get(product=product_id, course=course_id).delete()
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(detail=False, methods=["POST"])
    def reorder(self, request, *args, **kwargs):  # pylint: disable=no-self-use, unused-argument
        """
        Allow to reorder target_courses for a product
        """
        product_id = kwargs.get("product_id")
        target_course_ids = request.data.pop("target_courses")
        all_target_courses = models.ProductTargetCourseRelation.objects.filter(
            product=product_id, course__in=target_course_ids
        )
        if len(all_target_courses) != len(target_course_ids):
            return Response(
                {
                    "target_courses": (
                        "target_courses do not match "
                        f"those on product id {product_id}"
                    )
                },
                status=HTTPStatus.BAD_REQUEST,
            )
        for index, target_course_id in enumerate(target_course_ids):
            models.ProductTargetCourseRelation.objects.filter(
                product=product_id, course=target_course_id
            ).update(position=index)
        return Response(status=HTTPStatus.CREATED)


class ContractDefinitionViewSet(viewsets.ModelViewSet):
    """
    Admin Contract Definition ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminContractDefinitionSerializer
    queryset = models.ContractDefinition.objects.all()
    filterset_class = filters.ContractDefinitionAdminFilterSet


class CourseProductRelationViewSet(viewsets.ModelViewSet):
    """
    CourseProductRelation ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCourseProductRelationsSerializer
    queryset = models.CourseProductRelation.objects.all().select_related(
        "course", "product"
    )
    ordering = "created_on"

    @staticmethod
    def get_request_schema_parameters(create=False):
        """
        Return the parameters to use in the OpenAPI schema.
        """
        return [
            OpenApiParameter(
                name="course_id",
                required=create,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="product_id",
                required=create,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="organization_ids",
                required=False,
                type=OpenApiTypes.UUID,
                many=True,
            ),
        ]

    @extend_schema(parameters=get_request_schema_parameters(create=True))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(parameters=get_request_schema_parameters())
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(parameters=get_request_schema_parameters())
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete the relation between course_id and product_id
        """
        try:
            return super().destroy(request, *args, **kwargs)
        except ValidationError as error:
            return Response(
                {"detail": str(error)},
                status=HTTPStatus.FORBIDDEN,
            )


class NestedCourseProductRelationOrderGroupViewSet(
    SerializerPerActionMixin,
    viewsets.ModelViewSet,
    NestedGenericViewSet,
):
    """
    OrderGroup ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_classes = {
        "create": serializers.AdminOrderGroupCreateSerializer,
    }
    default_serializer_class = serializers.AdminOrderGroupSerializer
    queryset = models.OrderGroup.objects.all().select_related("course_product_relation")
    ordering = "created_on"
    lookup_fields = ["course_product_relation", "pk"]
    lookup_url_kwargs = ["course_product_relation_id", "pk"]

    def create(self, request, *args, **kwargs):
        """
        Create a new OrderGroup using the course_product_relation_id from the URL
        """
        data = request.data
        data["course_product_relation"] = kwargs.get("course_product_relation_id")
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTPStatus.CREATED, headers=headers)


class OrderViewSet(
    SerializerPerActionMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Admin Order ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_classes = {
        "list": serializers.AdminOrderLightSerializer,
    }
    default_serializer_class = serializers.AdminOrderSerializer
    filterset_class = filters.OrderAdminFilterSet
    queryset = models.Order.objects.all().select_related(
        "product",
        "owner",
        "course",
        "organization",
        "enrollment",
        "enrollment__course_run",
        "contract",
        "contract__definition",
        "certificate",
        "certificate__certificate_definition",
        "order_group",
    )
    ordering = "created_on"

    def destroy(self, request, *args, **kwargs):
        """Cancels an order."""
        order = self.get_object()
        order.cancel()
        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        request=None,
        responses={
            (200, "application/json"): serializers.AdminCertificateSerializer,
            (201, "application/json"): serializers.AdminCertificateSerializer,
            404: serializers.ErrorResponseSerializer,
            422: serializers.ErrorResponseSerializer,
        },
    )
    @action(methods=["POST"], detail=True)
    def generate_certificate(self, request, pk=None):  # pylint:disable=unused-argument
        """
        Generate the certificate for an order when it is eligible.
        """
        order = self.get_object()

        certificate, created = order.get_or_generate_certificate()

        if not certificate:
            return JsonResponse(
                {"details": f"Cannot issue certificate for order {order.id}"},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        certificate = serializers.AdminCertificateSerializer(certificate).data
        if not created:
            return Response(certificate, status=HTTPStatus.OK)

        return Response(certificate, status=HTTPStatus.CREATED)


class OrganizationAddressViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Write only Address for Organizations ViewSet.
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminOrganizationAddressSerializer
    queryset = models.Address.objects.filter(owner__isnull=True).select_related(
        "organization"
    )
    ordering = "created_on"

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        context["organization_id"] = self.kwargs["organization_id"]
        return context

    def destroy(self, request, *args, **kwargs):
        """
        Delete the address of an organization when the relation exists only.
        """
        address = self.get_object()
        organization_id = self.kwargs["organization_id"]

        try:
            models.Address.objects.get(pk=address.pk, organization_id=organization_id)
        except models.Address.DoesNotExist as error:
            raise ValidationError(
                "The relation does not exist between the address and the organization."
            ) from error

        return super().destroy(request, *args, **kwargs)
