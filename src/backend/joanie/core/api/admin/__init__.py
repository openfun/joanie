"""
Admin API Endpoints
"""

from http import HTTPStatus

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import (
    mixins,
    permissions,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from sentry_sdk import capture_exception

from joanie.core import enums, filters, models, serializers
from joanie.core.api.base import NestedGenericViewSet, SerializerPerActionMixin
from joanie.core.authentication import SessionAuthenticationWithAuthenticateHeader
from joanie.core.exceptions import CertificateGenerationError
from joanie.core.tasks import (
    generate_certificates_task,
    update_organization_signatories_contracts_task,
)
from joanie.core.utils.course_product_relation import (
    get_generated_certificates,
    get_orders,
)
from joanie.core.utils.payment_schedule import (
    get_transaction_references_to_refund,
    has_installment_paid,
)
from joanie.payment import get_payment_backend

from .enrollment import EnrollmentViewSet


class AliasOrderingFilter(OrderingFilter):
    """
    Custom filter to handle aliases in ordering fields.
    """

    def remove_invalid_fields(self, queryset, fields, view, request):
        """
        Remove invalid fields from the ordering list.
        """
        if not hasattr(view, "ordering_aliases"):
            return super().remove_invalid_fields(queryset, fields, view, request)

        valid_fields = []
        for term in fields:
            # Strip a potential '-' from the beginning.
            prefix = "-" if term.startswith("-") else ""
            field = term.lstrip("-")
            # Replace the alias if needed.
            if field in view.ordering_aliases:
                field = view.ordering_aliases[field]
            valid_fields.append(prefix + field)

        return valid_fields


# pylint: disable=too-many-ancestors
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Admin Organization ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminOrganizationSerializer
    queryset = models.Organization.objects.all()
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]
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
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

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
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

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
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]


class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Admin User ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminUserSerializer
    me_serializer_class = serializers.AdminUserCompleteSerializer
    queryset = models.User.objects.all()
    filterset_class = filters.UserAdminFilterSet
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

    def get_queryset(self):
        """
        Only return users if a query is provided to filter them.
        """
        if not self.request.query_params.get(
            "query", None
        ) and not self.request.query_params.get("ids", None):
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
    NestedGenericViewSet,
):
    """
    Write only Course Access ViewSet
    """

    lookup_fields = ["course__pk", "pk"]
    lookup_url_kwargs = ["course_id", "pk"]
    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminCourseAccessSerializer
    queryset = models.CourseAccess.objects.all().select_related("user")
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

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
    NestedGenericViewSet,
):
    """
    Write only Organization Access ViewSet
    """

    lookup_fields = ["organization_id", "pk"]
    lookup_url_kwargs = ["organization_id", "pk"]
    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminOrganizationAccessSerializer
    queryset = models.OrganizationAccess.objects.all().select_related("user")
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        context["organization_id"] = self.kwargs["organization_id"]
        return context

    def perform_create(self, serializer):
        """
        Creates organization access and updates the organization signatories
        for ongoing signature procedures when the role is 'owner'.
        """
        instance = serializer.save()

        if instance.role == enums.OWNER:
            update_organization_signatories_contracts_task.delay(
                organization_id=instance.organization_id
            )

    def perform_update(self, serializer):
        """
        Updates the organization access and may trigger adjustments to the organization's
        signatories for ongoing signature procedures.
        Such adjustments occur when there is a change in the instance user's role, specifically
        when transitioning to or from the 'owner' role.
        """
        instance_role_before_update = serializer.instance.role
        serializer.save()

        if any(
            role == enums.OWNER
            for role in (instance_role_before_update, serializer.instance.role)
        ):
            try:
                # ruff : noqa : BLE001
                # pylint: disable=broad-exception-caught
                update_organization_signatories_contracts_task.delay(
                    organization_id=serializer.instance.organization_id
                )
            except Exception as error:
                capture_exception(error)

    def perform_destroy(self, instance):
        """
        Deletes organization access and update the signatories of the organization
        when the deleted instance had the role 'owner'.
        """
        instance.delete()

        if instance.role == enums.OWNER:
            try:
                # ruff : noqa : BLE001
                # pylint: disable=broad-exception-caught
                update_organization_signatories_contracts_task.delay(
                    organization_id=instance.organization_id
                )
            except Exception as error:
                capture_exception(error)


class TargetCoursesViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    NestedGenericViewSet,
):
    """
    Write only Product's TargetCourse ViewSet
    """

    lookup_fields = ["product__pk", "pk"]
    lookup_url_kwargs = ["product_id", "pk"]
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
                        f"target_courses do not match those on product id {product_id}"
                    )
                },
                status=HTTPStatus.BAD_REQUEST,
            )
        for index, target_course_id in enumerate(target_course_ids):
            models.ProductTargetCourseRelation.objects.filter(
                product=product_id, course=target_course_id
            ).update(position=index)
        return Response(status=HTTPStatus.CREATED)


class TeacherViewSet(viewsets.ModelViewSet):
    """
    Admin Teacher ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminTeacherSerializer
    queryset = models.Teacher.objects.all()
    filterset_class = filters.TeacherAdminFilterSet
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]


class SkillViewSet(viewsets.ModelViewSet):
    """
    Admin Skill ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminSkillSerializer
    queryset = models.Skill.objects.all()
    filterset_class = filters.SkillAdminFilterSet
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]
    ordering_fields = ["translations__title"]


class ContractDefinitionViewSet(viewsets.ModelViewSet):
    """
    Admin Contract Definition ViewSet
    """

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminContractDefinitionSerializer
    queryset = models.ContractDefinition.objects.all()
    filterset_class = filters.ContractDefinitionAdminFilterSet
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]


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

    @extend_schema(
        request=None,
        responses={
            (200, "application/json"): OpenApiTypes.OBJECT,
            404: serializers.ErrorResponseSerializer,
        },
    )
    @action(methods=["GET"], detail=True)
    def check_certificates_generation_process(self, request, pk=None):  # pylint:disable=unused-argument
        """
        Checks whether the Celery task for generating certificates is in progress or completed.
        If cached data is found, it indicates that the generation process is ongoing. Otherwise,
        it signifies that the task has been completed or has not been requested.
        """
        course_product_relation = self.get_object()

        if cache_data := cache.get(
            f"celery_certificate_generation_{course_product_relation.id}"
        ):
            return JsonResponse(cache_data, status=HTTPStatus.OK)

        return JsonResponse(
            {"details": "No cache data found."}, status=HTTPStatus.NOT_FOUND
        )

    @extend_schema(
        request=None,
        responses={
            (201, "application/json"): OpenApiTypes.OBJECT,
            (202, "application/json"): OpenApiTypes.OBJECT,
            400: serializers.ErrorResponseSerializer,
        },
    )
    @action(methods=["POST"], detail=True)
    def generate_certificates(self, request, pk=None):  # pylint:disable=unused-argument
        """
        Generate the certificates for a course product relation when it is eligible.
        """
        course_product_relation = self.get_object()
        cache_key = f"celery_certificate_generation_{course_product_relation.id}"

        if cache_data := cache.get(cache_key):
            return JsonResponse(cache_data, status=HTTPStatus.ACCEPTED)

        # Prepare cache data before trigger celery's task.
        orders_ids = get_orders(course_product_relation)
        certificates_published = get_generated_certificates(course_product_relation)
        cache_data = {
            "course_product_relation_id": str(course_product_relation.id),
            "count_certificate_to_generate": len(orders_ids),
            "count_exist_before_generation": certificates_published.count(),
        }
        cache.set(cache_key, cache_data)

        try:
            # ruff : noqa: BLE001
            # pylint: disable=broad-exception-caught
            generate_certificates_task.delay(order_ids=orders_ids, cache_key=cache_key)
        except Exception as error:
            cache.delete(cache_key)
            capture_exception(error)
            return JsonResponse({"details": str(error)}, status=HTTPStatus.BAD_REQUEST)

        return JsonResponse(cache_data, status=HTTPStatus.CREATED)


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
        "update": serializers.AdminOrderGroupUpdateSerializer,
        "partial_update": serializers.AdminOrderGroupUpdateSerializer,
    }
    default_serializer_class = serializers.AdminOrderGroupSerializer
    queryset = models.OrderGroup.objects.all().select_related(
        "course_product_relation", "discount"
    )
    ordering = "created_on"
    lookup_fields = ["course_product_relation", "pk"]
    lookup_url_kwargs = ["course_product_relation_id", "pk"]

    def create(self, request, *args, **kwargs):
        """
        Create a new OrderGroup using the course_product_relation_id from the URL
        """
        data = request.data
        data["course_product_relation"] = kwargs.get("course_product_relation_id")
        if "nb_seats" in data and not data.get("nb_seats"):
            data.pop("nb_seats")
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
        "export": serializers.AdminOrderExportSerializer,
    }
    serializer_class = serializers.AdminOrderSerializer
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
        "credit_card",
    )

    # Map aliases to actual model field lookups.
    # For instance, the query parameter "product_title" will map to "product__translations__title"
    ordering_aliases = {
        "owner_name": "owner__first_name",
        "product_title": "product__translations__title",
        "organization_title": "organization__translations__title",
    }
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

    def destroy(self, request, *args, **kwargs):
        """Cancels an order."""
        order = self.get_object()
        order.flow.cancel()
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
        try:
            certificate, created = order.get_or_generate_certificate()
        except CertificateGenerationError as error:
            return JsonResponse(
                {"details": str(error)},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        certificate = serializers.AdminCertificateSerializer(certificate).data
        if not created:
            return Response(certificate, status=HTTPStatus.OK)

        return Response(certificate, status=HTTPStatus.CREATED)

    @action(methods=["POST"], detail=True)
    def refund(self, request, pk=None):  # pylint:disable=unused-argument
        """
        Refund an order only if the order is in state 'cancel' and at least 1 installment
        has been paid in the payment schedule.
        """
        order = self.get_object()

        order.flow.refunding()

        payment_backend = get_payment_backend()
        transaction_references_to_refund = get_transaction_references_to_refund(order)
        for reference, installment in transaction_references_to_refund.items():
            payment_backend.cancel_or_refund(
                amount=installment["amount"],
                reference=reference,
                installment_reference=installment["id"],
            )

        return Response(status=HTTPStatus.ACCEPTED)

    @extend_schema(
        request=None,
        responses={
            (200, "text/csv"): OpenApiTypes.OBJECT,
            404: serializers.ErrorResponseSerializer,
        },
    )
    @action(methods=["GET"], detail=False)
    def export(self, request):
        """
        Export orders to a CSV file.
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = serializers.AdminOrderListExportSerializer(
            queryset.iterator(), child=self.get_serializer()
        )
        now = timezone.now().strftime("%d-%m-%Y_%H-%M-%S")
        return StreamingHttpResponse(
            serializer.csv_stream(),
            content_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="orders_{now}.csv"'},
        )


class OrganizationAddressViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    NestedGenericViewSet,
):
    """
    Write only Address for Organizations ViewSet.
    """

    lookup_fields = ["organization__pk", "pk"]
    lookup_url_kwargs = ["organization_id", "pk"]
    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminOrganizationAddressSerializer
    queryset = models.Address.objects.filter(owner__isnull=True).select_related(
        "organization"
    )
    filter_backends = [DjangoFilterBackend, AliasOrderingFilter]

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


class DiscountViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Admin Discount Viewset"""

    authentication_classes = [SessionAuthenticationWithAuthenticateHeader]
    permission_classes = [permissions.IsAdminUser & permissions.DjangoModelPermissions]
    serializer_class = serializers.AdminDiscountSerializer
    queryset = models.Discount.objects.all()
    filterset_class = filters.DiscountAdminFilterSet
