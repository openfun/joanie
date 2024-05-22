"""
Client API endpoints
"""

# pylint: disable=too-many-ancestors, too-many-lines, too-many-branches
# ruff: noqa: PLR0911,PLR0912
import io
import uuid
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework import permissions as drf_permissions
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from joanie.core import enums, filters, models, permissions, serializers
from joanie.core.api.base import NestedGenericViewSet
from joanie.core.exceptions import NoContractToSignError
from joanie.core.models import Address
from joanie.core.tasks import generate_zip_archive_task
from joanie.core.utils import contract as contract_utility
from joanie.core.utils import contract_definition, issuers
from joanie.core.utils.payment_schedule import generate as generate_payment_schedule
from joanie.core.utils.signature import check_signature
from joanie.payment import enums as payment_enums
from joanie.payment import get_payment_backend
from joanie.payment.models import CreditCard, Invoice

UUID_REGEX = (
    "[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
)


class CourseRunViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """API ViewSet for all interactions with course runs."""

    lookup_field = "id"
    permissions_classes = [drf_permissions.AllowAny]
    queryset = models.CourseRun.objects.filter(is_listed=True).select_related("course")
    serializer_class = serializers.CourseRunSerializer
    ordering = ["-created_on"]

    def get_queryset(self):
        """
        Allow to get a list of course runs only from the nested route under a course.
        """
        queryset = super().get_queryset()
        course_id = self.kwargs.get("course_id")

        if self.action == "list" and not course_id:
            raise NotFound("The requested resource was not found on this server.")

        if course_id:
            queryset = queryset.filter(course=course_id)

        return queryset


class CourseProductRelationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    API ViewSet for all interactions with course-product relations.
    Can be accessed through multiple URLs
    GET /courses/
        Return all courses the user has access to
    GET /organizations/<organization_id>/courses/
        Return all courses from the specified organization if user
        has access to the organization
    """

    lookup_field = "pk"
    lookup_url_kwarg = "pk_or_product_id"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CourseProductRelationSerializer
    filterset_class = filters.CourseProductRelationViewSetFilter
    ordering = ["-created_on"]
    queryset = (
        models.CourseProductRelation.objects.filter(
            organizations__isnull=False,
        )
        .select_related(
            "course",
            "product",
            "product__contract_definition",
            "product__certificate_definition",
        )
        .prefetch_related("organizations")
        .distinct()
    )

    @property
    def course_lookup_filter(self):
        """
        Return the filter field to use to get the course object.
        """
        try:
            uuid.UUID(self.kwargs["course_id"])
        except ValueError:
            lookup_filter = "course__code__iexact"
        else:
            lookup_filter = "course__pk"

        return lookup_filter

    def get_object(self):
        """
        The retrieve action is used to get a single course product relation.
        There are two cases to handle :
        1. Retrieve the relation through its id
        2. Retrieve the relation through its course id and product id
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if course_id := self.kwargs.get("course_id"):
            # 1. Request through a nested course route, we want to retrieve
            # a relation through its course id and product id
            filter_kwargs = {
                self.course_lookup_filter: course_id,
                "product__id": self.kwargs[lookup_url_kwarg],
            }
        else:
            # 2. Request through the course product relation route, we want to retrieve
            # a relation through its id
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    @property
    def username(self):
        """Get the authenticated username from the request."""
        return (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

    def get_queryset(self):
        """
        The queryset filter depends on the action as to list course product relation we
        only want to list course product relation to which the user has access.
        """
        queryset = super().get_queryset()

        if course_id := self.kwargs.get("course_id"):
            queryset = queryset.filter(**{self.course_lookup_filter: course_id})

        if organization_id := self.kwargs.get("organization_id"):
            queryset = queryset.filter(
                organizations__id=organization_id,
                organizations__accesses__user__username=self.username,
            )
        elif self.action == "list" or self.action == "retrieve" and not course_id:
            queryset = queryset.filter(course__accesses__user__username=self.username)

        return queryset

    def get_permissions(self):
        """Anonymous user should be able to retrieve a course product relation."""
        if (
            self.action == "retrieve"
            and self.kwargs.get("course_id")
            or self.action == "payment_schedule"
        ):
            permission_classes = [drf_permissions.AllowAny]
        else:
            return super().get_permissions()

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """Return the serializer class to use."""
        if self.action == "payment_schedule":
            return serializers.OrderPaymentScheduleSerializer
        return self.serializer_class

    @action(detail=True, methods=["GET"], url_path="payment-schedule")
    def payment_schedule(self, *args, **kwargs):
        """
        Return the payment schedule for a course product relation.
        """
        course_product_relation = self.get_object()
        course_run_dates = (
            course_product_relation.product.get_equivalent_course_run_dates()
        )
        payment_schedule = generate_payment_schedule(
            course_product_relation.product.price,
            timezone.now(),
            course_run_dates["start"],
            course_run_dates["end"],
        )

        serializer = self.get_serializer(data={"payment_schedule": payment_schedule})
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data.get("payment_schedule"))


class EnrollmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """API ViewSet for all interactions with enrollments."""

    lookup_field = "id"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.EnrollmentSerializer
    filterset_class = filters.EnrollmentViewSetFilter

    def get_queryset(self):
        """
        Custom queryset to limit to enrollments owned by the logged-in user.
        We retrieve product relations related to each enrollment in the same
        query using a prefetch query.
        """
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        return (
            models.Enrollment.objects.filter(user__username=username)
            .select_related("course_run__course")
            .prefetch_related(
                "certificate",
                "related_orders",
                Prefetch(
                    "course_run__course__product_relations",
                    queryset=models.CourseProductRelation.objects.select_related(
                        "product",
                        "product__contract_definition",
                    ).filter(product__type=enums.PRODUCT_TYPE_CERTIFICATE),
                    to_attr="certificate_product_relations",
                ),
            )
        )

    def perform_create(self, serializer):
        """
        Force the enrollment's "owner" field to the logged-in user and synchronize the
        enrollment with the LMS.
        """
        serializer.save(user=self.request.user)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API view for a user to consult the orders he/she owns or create a new one.

    GET /api/orders/
        Return list of all orders for a user with pagination

    POST /api/orders/ with expected data:
        - course: course code
        - product: product id (product must be associated to the course. Otherwise,
          a 400 error is returned)
        Return new order just created

    POST /api/orders/:order_id/submit_for_signature/
        Return an invitation link to sign the contract definition
    """

    lookup_field = "pk"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.OrderSerializer
    filterset_class = filters.OrderViewSetFilter
    ordering = ["-created_on"]

    def get_queryset(self):
        """Custom queryset to limit to orders owned by the logged-in user."""
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        return models.Order.objects.filter(owner__username=username).select_related(
            "certificate",
            "contract",
            "course",
            "enrollment__course_run__course",
            "organization",
            "owner",
            "product",
        )

    def perform_create(self, serializer):
        """Force the order's "owner" field to the logged-in user."""
        serializer.save(owner=self.request.user)

    def _get_organization_with_least_active_orders(
        self, product, course, enrollment=None
    ):
        """
        Return the organization with the least not canceled order count
        for a given product and course.
        """
        if enrollment:
            clause = Q(order__enrollment=enrollment)
        else:
            clause = Q(order__course=course)

        order_count = Count(
            "order",
            filter=clause
            & Q(order__product=product)
            & ~Q(order__state=enums.ORDER_STATE_CANCELED),
        )

        try:
            course_relation = product.course_relations.get(
                course_id=course.id if course else enrollment.course_run.course_id
            )
        except models.CourseProductRelation.DoesNotExist:
            return None

        try:
            return (
                course_relation.organizations.annotate(order_count=order_count)
                .order_by("order_count")
                .first()
            )
        except models.Organization.DoesNotExist:
            return None

    # pylint: disable=too-many-return-statements
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Try to create an order and a related payment if the payment is fee."""
        enrollment = None
        if enrollment_id := request.data.get("enrollment_id"):
            try:
                enrollment = models.Enrollment.objects.get(id=enrollment_id)
            except models.Enrollment.DoesNotExist:
                return Response(
                    {"enrollment_id": f"Enrollment with id {enrollment_id} not found."},
                    status=HTTPStatus.BAD_REQUEST,
                )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)

        course_code = serializer.initial_data.get("course_code")

        product = serializer.validated_data.get("product")

        serializer.validated_data["enrollment"] = enrollment

        # Retrieve course instance from the provided course code
        if course_code:
            try:
                course = models.Course.objects.get(code=course_code)
            except models.Course.DoesNotExist:
                return Response(
                    {"course": ["Course with code {course_code} does not exist."]},
                    status=HTTPStatus.BAD_REQUEST,
                )
            serializer.validated_data["course"] = course
        else:
            if not enrollment:
                return Response(
                    {
                        "__all__": [
                            "Either the course or the enrollment field is required."
                        ]
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            course = enrollment.course_run.course

        if not serializer.initial_data.get("organization_id"):
            organization = self._get_organization_with_least_active_orders(
                product, course, enrollment
            )
            if organization:
                serializer.initial_data["organization_id"] = organization.id

        if product.price != 0 and not request.data.get("billing_address"):
            return Response(
                {"billing_address": "This field is required."},
                status=HTTPStatus.BAD_REQUEST,
            )

        # - Validate data then create an order
        try:
            self.perform_create(serializer)
        except (DRFValidationError, IntegrityError):
            return Response(
                (
                    f"Cannot create order related to the product {product.id} "
                    f"and course {course.code}"
                ),
                status=HTTPStatus.BAD_REQUEST,
            )

        serializer.instance.flow.assign(
            billing_address=request.data.get("billing_address")
        )

        # Else return the fresh new order
        return Response(serializer.data, status=HTTPStatus.CREATED)

    @action(detail=True, methods=["PATCH"])
    def submit(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """
        Submit a draft order if the conditions are filled
        """
        billing_address = (
            models.Address(**request.data.get("billing_address"))
            if request.data.get("billing_address")
            else None
        )
        credit_card_id = request.data.get("credit_card_id")
        order = self.get_object()

        return Response(
            {"payment_info": order.submit(billing_address, credit_card_id)},
            status=HTTPStatus.CREATED,
        )

    @action(detail=True, methods=["POST"])
    def abort(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """Change the state of the order to pending"""
        payment_id = request.data.get("payment_id")

        order = self.get_object()

        if order.state == enums.ORDER_STATE_VALIDATED:
            return Response(
                "Cannot abort a validated order.",
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        order.flow.pending(payment_id)

        return Response(status=HTTPStatus.NO_CONTENT)

    @action(detail=True, methods=["POST"])
    def cancel(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """Change the state of the order to cancelled"""
        order = self.get_object()

        if order.state == enums.ORDER_STATE_VALIDATED:
            return Response(
                "Cannot cancel a validated order.",
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        order.flow.cancel()
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(detail=True, methods=["GET"])
    def invoice(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name
        """
        Retrieve an invoice through its reference if it is related to
        the order instance and owned by the authenticated user.
        """
        reference = request.query_params.get("reference")

        if reference is None:
            return Response(
                {"reference": "This parameter is required."},
                status=HTTPStatus.BAD_REQUEST,
            )

        username = request.auth["username"] if request.auth else request.user.username
        try:
            invoice = Invoice.objects.get(
                reference=reference,
                order__id=pk,
                order__owner__username=username,
            )
        except Invoice.DoesNotExist:
            return Response(
                (f"No invoice found for order {pk} with reference {reference}."),
                status=HTTPStatus.NOT_FOUND,
            )

        context = invoice.get_document_context()
        invoice_pdf_bytes = issuers.generate_document(
            name=payment_enums.INVOICE_TYPE_INVOICE, context=context
        )

        response = HttpResponse(
            invoice_pdf_bytes, content_type="application/pdf", status=HTTPStatus.OK
        )
        response["Content-Disposition"] = (
            f"attachment; filename={invoice.reference}.pdf;"
        )

        return response

    @action(detail=True, methods=["PUT"])
    def validate(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """
        Validate the order
        """
        order = self.get_object()
        order.flow.validate()
        return Response(status=HTTPStatus.OK)

    @extend_schema(request=None)
    @action(detail=True, methods=["POST"])
    def submit_for_signature(self, request, pk=None):  # pylint: disable=no-self-use, unused-argument, invalid-name
        """
        Create the contract of a product's order that has a contract definition and submit
        the contract to the signature provider. It returns a one-time use invitation link.
        """
        order = self.get_object()

        invitation_link = order.submit_for_signature(request.user)

        return JsonResponse({"invitation_link": invitation_link}, status=HTTPStatus.OK)

    @extend_schema(
        request=None,
        responses={
            204: OpenApiTypes.NONE,
            422: serializers.ErrorResponseSerializer,
        },
    )
    @action(detail=True, methods=["POST"])
    def withdraw(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """Withdraw an order"""
        order = self.get_object()

        try:
            order.withdraw()
        except ValidationError as error:
            return Response(
                {"detail": f"{error}"}, status=HTTPStatus.UNPROCESSABLE_ENTITY
            )

        return Response(status=HTTPStatus.NO_CONTENT)

    @extend_schema(
        request=None,
        responses={
            (200, "application/json"): OpenApiTypes.OBJECT,
            404: serializers.ErrorResponseSerializer,
            422: serializers.ErrorResponseSerializer,
        },
    )
    @action(detail=True, methods=["POST"], url_path="submit-installment-payment")
    def submit_installment_payment(self, request, pk=None):  # pylint: disable=unused-argument
        """
        Submit a payment for a failed installment that was scheduled for a given order.
        """
        order = self.get_object()
        if order.state not in [
            enums.ORDER_STATE_NO_PAYMENT,
            enums.ORDER_STATE_FAILED_PAYMENT,
        ]:
            return Response(
                {"detail": "The order is not in failed payment state."},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        installment = order.get_first_installment_refused()
        if not installment:
            return Response(
                {"detail": "No installment found with a refused payment state."},
                status=HTTPStatus.BAD_REQUEST,
            )

        payment_backend = get_payment_backend()
        credit_card_id = request.data.get("credit_card_id")
        if not credit_card_id:
            payment_infos = payment_backend.create_payment(
                order=order,
                billing_address=order.main_invoice.recipient_address,
                installment=installment,
            )

            return Response(payment_infos, status=HTTPStatus.OK)

        try:
            credit_card = CreditCard.objects.get_card_for_owner(
                pk=credit_card_id,
                username=order.owner.username,
            )
        except CreditCard.DoesNotExist:
            return Response(
                {"detail": "Credit card does not exist."},
                status=HTTPStatus.NOT_FOUND,
            )

        payment_infos = payment_backend.create_one_click_payment(
            order=order,
            billing_address=order.main_invoice.recipient_address,
            credit_card_token=credit_card.token,
            installment=installment,
        )

        return Response(payment_infos, status=HTTPStatus.OK)


class AddressViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API view allows to get all addresses or create or update a new one for a user.

    GET /api/addresses/
        Return list of all addresses for a user

    POST /api/addresses/ with expected data:
        - address: str
        - city: str
        - country: str, country code
        - first_name: str, recipient first name
        - last_name: str, recipient last name
        - is_main?: bool, if True set address as main
        - postcode: str
        - title: str, address title
        Return new address just created

    PUT /api/addresses/<address_id>/ with expected data:
        - address: str
        - city: str
        - country: str, country code
        - first_name: str, recipient first name
        - last_name: str, recipient last name
        - is_main?: bool, if True set address as main
        - postcode: str
        - title: str, address title
        Return address just updated

    DELETE /api/addresses/<address_id>/
        Delete selected address
    """

    lookup_field = "id"
    serializer_class = serializers.AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Custom queryset to get user addresses"""
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        return models.Address.objects.filter(owner__username=username, is_reusable=True)

    def perform_create(self, serializer):
        """Create a new address for user authenticated"""
        serializer.save(owner=self.request.user, is_reusable=True)

    def destroy(self, request, *args, **kwargs):
        """
        Delete an address for user authenticated. If the address is linked to
        invoices it is not deleted but marked as not reusable.
        """
        instance = self.get_object()

        if instance.invoices.count() > 0:
            instance.is_main = False
            instance.is_reusable = False
            instance.save()

            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        self.perform_destroy(instance)
        return Response(status=HTTPStatus.NO_CONTENT)


class CertificateViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    API views to get all certificates for a user

    GET /api/certificates/:certificate_id
        Return list of all certificates for a user or one certificate if an id is
        provided.

    GET /api/certificates/:certificate_id/download
        Return the certificate document in PDF format.
    """

    lookup_field = "pk"
    serializer_class = serializers.CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = filters.CertificateViewSetFilter
    queryset = models.Certificate.objects.all().select_related(
        "certificate_definition",
        "order__course",
        "order__enrollment__course_run__course",
        "order__organization",
        "order__owner",
        "order__product",
        "enrollment__course_run__course",
    )

    def get_username(self):
        """Get the authenticated username from the request."""
        return (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == "list":
            queryset = queryset.distinct()

        return queryset

    def get_object(self):
        """Allow getting a certificate by its pk."""
        queryset = self.get_queryset()
        certificate = get_object_or_404(queryset, pk=self.kwargs["pk"])
        username = self.get_username()

        if certificate.order and certificate.order.owner.username != username:
            raise Http404("No Certificate matches the given query.")

        if certificate.enrollment and certificate.enrollment.user.username != username:
            raise Http404("No Certificate matches the given query.")
        # May raise a permission denied
        self.check_object_permissions(self.request, certificate)

        return certificate

    @extend_schema(
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            404: serializers.ErrorResponseSerializer,
            422: serializers.ErrorResponseSerializer,
        },
    )
    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name
        """
        Retrieve a certificate through its id if it is owned by the authenticated user.
        """
        certificate = self.get_object()

        try:
            context = certificate.get_document_context()
        except ValueError:
            return Response(
                {"detail": f"Unable to generate certificate {pk}."},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        document = issuers.generate_document(
            name=certificate.certificate_definition.template, context=context
        )

        response = HttpResponse(
            document, content_type="application/pdf", status=HTTPStatus.OK
        )

        response["Content-Disposition"] = f"attachment; filename={pk}.pdf;"

        return response


class OrganizationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API ViewSet for all interactions with organizations.

    GET /api/organizations/:organization_id
        Return list of all organizations related to the logged-in user or one organization
        if an id is provided.
    """

    lookup_field = "pk"
    permission_classes = [permissions.AccessPermission]
    serializer_class = serializers.OrganizationSerializer
    filterset_class = filters.OrganizationViewSetFilter

    def get_queryset(self):
        """
        Custom queryset to get user organizations
        """
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        user_role_query = models.OrganizationAccess.objects.filter(
            user__username=username, organization=OuterRef("pk")
        ).values("role")[:1]
        return models.Organization.objects.filter(
            accesses__user__username=username
        ).annotate(user_role=Subquery(user_role_query))

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="contract_ids",
                description="List of contract ids to sign, "
                "if not provided all the available contracts will be signed.",
                required=False,
                type=OpenApiTypes.UUID,
                many=True,
            ),
            OpenApiParameter(
                name="course_product_relation_ids",
                description="List of course product relation ids to sign related contracts, "
                "if not provided all the available contracts will be signed.",
                required=False,
                type=OpenApiTypes.UUID,
                many=True,
            ),
        ],
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="contracts-signature-link",
        permission_classes=[permissions.CanSignOrganizationContracts],
    )
    def contracts_signature_link(self, request, *args, **kwargs):
        """
        Return an invitation link to sign all the available contracts for the organization.
        """
        organization = self.get_object()
        contract_ids = request.query_params.getlist("contract_ids")
        course_product_relation_ids = request.query_params.getlist(
            "course_product_relation_ids"
        )

        try:
            (signature_link, ids) = organization.contracts_signature_link(
                request.user,
                contract_ids=contract_ids,
                course_product_relation_ids=course_product_relation_ids,
            )
        except NoContractToSignError as error:
            return Response({"detail": f"{error}"}, status=HTTPStatus.BAD_REQUEST)

        return JsonResponse(
            {
                "invitation_link": signature_link,
                "contract_ids": ids,
            },
            status=HTTPStatus.OK,
        )


class OrganizationAccessViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    NestedGenericViewSet,
):
    """
    API ViewSet for all interactions with organization accesses.

    GET /api/organization/<organization_id>/accesses/:<organization_access_id>
        Return list of all organization accesses related to the logged-in user or one
        organization access if an id is provided.

    POST /api/<organization_id>/accesses/ with expected data:
        - user: str
        - role: str [owner|admin|member]
        Return newly created organization access

    PUT /api/<organization_id>/accesses/<organization_access_id>/ with expected data:
        - role: str [owner|admin|member]
        Return updated organization access

    PATCH /api/<organization_id>/accesses/<organization_access_id>/ with expected data:
        - role: str [owner|admin|member]
        Return partially updated organization access

    DELETE /api/<organization_id>/accesses/<organization_access_id>/
        Delete targeted organization access
    """

    lookup_fields = ["organization__pk", "pk"]
    lookup_url_kwargs = ["organization_id", "pk"]
    permission_classes = [permissions.AccessPermission]
    queryset = models.OrganizationAccess.objects.all().select_related("user")
    serializer_class = serializers.OrganizationAccessSerializer

    def get_permissions(self):
        """User only needs to be authenticated to list organization accesses"""
        if self.action == "list":
            permission_classes = [permissions.IsAuthenticated]
        else:
            return super().get_permissions()

        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        context = super().get_serializer_context()
        context["organization_id"] = self.kwargs["organization_id"]
        return context

    def get_queryset(self):
        """Return the queryset according to the action."""
        queryset = super().get_queryset()
        queryset = queryset.filter(organization=self.kwargs["organization_id"])

        if self.action == "list":
            # Limit to accesses that are linked to an organization THAT has an access
            # for the logged-in user (not filtering the only access linked to the
            # logged-in user)
            user_role_query = models.OrganizationAccess.objects.filter(
                organization__accesses__user=self.request.user
            ).values("role")[:1]
            queryset = (
                queryset.filter(
                    organization__accesses__user=self.request.user,
                )
                .annotate(user_role=Subquery(user_role_query))
                .distinct()
            )
        return queryset


class CourseAccessViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    NestedGenericViewSet,
):
    """
    API ViewSet for all interactions with course accesses.

    GET /api/courses/<course_id|course_code>/accesses/:<course_access_id>
        Return list of all course accesses related to the logged-in user or one
        course access if an id is provided.

    POST /api/courses/<course_id|course_code>/accesses/ with expected data:
        - user: str
        - role: str [owner|admin|member]
        Return newly created course access

    PUT /api/courses/<course_id|course_code>/accesses/<course_access_id>/ with expected data:
        - role: str [owner|admin|member]
        Return updated course access

    PATCH /api/courses/<course_id|course_code>/accesses/<course_access_id>/ with expected data:
        - role: str [owner|admin|member]
        Return partially updated course access

    DELETE /api/courses/<course_id|course_code>/accesses/<course_access_id>/
        Delete targeted course access
    """

    lookup_fields = ["course__pk", "pk"]
    lookup_url_kwargs = ["course_id", "pk"]
    permission_classes = [permissions.AccessPermission]
    queryset = models.CourseAccess.objects.all().select_related("user")
    serializer_class = serializers.CourseAccessSerializer

    def get_permissions(self):
        """User only needs to be authenticated to list course accesses"""
        if self.action == "list":
            permission_classes = [permissions.IsAuthenticated]
        else:
            return super().get_permissions()

        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        context = super().get_serializer_context()
        context["course_id"] = self.kwargs["course_id"]
        return context

    def get_queryset(self):
        """Return the queryset according to the action."""
        queryset = super().get_queryset()
        queryset = queryset.filter(course=self.kwargs["course_id"])

        if self.action == "list":
            # Limit to accesses that are linked to a course THAT has an access
            # for the logged-in user (not filtering the only access linked to the
            # logged-in user)
            user_role_query = models.CourseAccess.objects.filter(
                course__accesses__user=self.request.user
            ).values("role")[:1]
            queryset = (
                queryset.filter(
                    course__accesses__user=self.request.user,
                )
                .annotate(user_role=Subquery(user_role_query))
                .distinct()
            )
        return queryset


class CourseViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    API ViewSet for all interactions with courses.

    GET /api/courses/
        Return list of all courses related to the logged-in user.

    GET /api/courses/:<course_id|course_code>
        Return one course if an id is provided.

    GET /api/courses/:<course_id|course_code>/wish
        Return wish status on this course for the authenticated user

    POST /api/courses/:<course_id|course_code>/wish
        Confirm a wish on this course for the authenticated user

    DELETE /api/courses/:<course_id|course_code>/wish
        Delete any existing wish on this course for the authenticated user
    """

    lookup_field = "pk"
    lookup_value_regex = "[0-9a-z-]*"
    filterset_class = filters.CourseViewSetFilter
    permission_classes = [permissions.AccessPermission]
    serializer_class = serializers.CourseSerializer
    ordering = ["-created_on"]

    @property
    def lookup_filter(self):
        """
        Return the filter field to use to get the course object.
        """
        try:
            uuid.UUID(self.kwargs["pk"])
        except ValueError:
            lookup_filter = "code__iexact"
        else:
            lookup_filter = "pk"

        return lookup_filter

    def get_object(self):
        """Allow getting a course by its pk or by its code."""
        queryset = self.filter_queryset(self.get_queryset())

        obj = get_object_or_404(queryset, **{self.lookup_filter: self.kwargs["pk"]})
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        """
        Custom queryset to get user courses
        """
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        # Get courses for an organization to which the user has access or courses
        # to which the user has access if no organization is targeted
        courses = models.Course.objects
        organization_id = self.kwargs.get("organization_id", None)
        if organization_id:
            courses = courses.filter(
                organizations__id=organization_id,
                organizations__accesses__user__username=username,
            )
        else:
            courses = courses.filter(accesses__user__username=username)

        # Retrieve the role of the logged-in user on each course in the same query
        user_role_query = models.CourseAccess.objects.filter(
            user__username=username, course=OuterRef("pk")
        ).values("role")[:1]
        return courses.annotate(user_role=Subquery(user_role_query)).prefetch_related(
            "organizations", "products", "course_runs"
        )

    @action(
        detail=True,
        methods=["post", "get", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    # pylint: disable=invalid-name
    def wish(self, request, pk=None):
        """Action to handle the wish on this course for the logged-in user."""
        course = get_object_or_404(
            models.Course.objects.all(), **{self.lookup_filter: pk}
        )
        params = {
            "course": course,
            "owner": request.user,
        }
        if request.method == "POST":
            models.CourseWish.objects.get_or_create(**params)
            is_wished = True
        elif request.method == "DELETE":
            models.CourseWish.objects.filter(**params).delete()
            is_wished = False
        else:
            is_wished = models.CourseWish.objects.filter(**params).exists()
        return Response({"status": is_wished})


class UserViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    User ViewSet
    """

    permission_classes = [permissions.AccessPermission]
    serializer_class = serializers.UserSerializer

    def get_queryset(self):
        """
        Only return users if a query is provided to filter them.
        """
        user = self.request.user

        return models.User.objects.get(id=user.id)

    @action(
        detail=False,
        methods=["get"],
        url_name="me",
        url_path="me",
        permission_classes=[permissions.IsAuthenticated],
    )
    def get_me(self, request):
        """
        Return information on currently logged user
        """
        context = {"request": request}
        return Response(self.serializer_class(request.user, context=context).data)


class GenericContractViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    The Generic API viewset to list & retrieve contracts.

    GET /.*/contracts/<uuid:contract_id>
    """

    lookup_field = "pk"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ContractSerializer
    filterset_class = filters.ContractViewSetFilter
    ordering = ["-student_signed_on", "-created_on"]
    queryset = models.Contract.objects.filter(
        order__state=enums.ORDER_STATE_VALIDATED
    ).select_related(
        "definition",
        "order__organization",
        "order__course",
        "order__enrollment__course_run__course",
        "order__owner",
        "order__product",
        "organization_signatory",
    )


class ContractViewSet(GenericContractViewSet):
    """
    Contract Viewset to list & retrieve contracts owned by the authenticated user.

    GET /api/contracts/
        Return list of all contracts owned by the logged-in user.

    GET /api/contracts/<contract_id>/
        Return a contract if one matches the provided id,
        and it is owned by the logged-in user.

    GET /api/contracts/<contract_id>/download/
        Return a contract in PDF format when it is signed on.
    """

    def get_queryset(self):
        """
        Customize the queryset to get only user's contracts.
        """
        queryset = super().get_queryset()

        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        query_filters = {"order__owner__username": username}

        return queryset.filter(**query_filters)

    @extend_schema(
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            404: serializers.ErrorResponseSerializer,
            422: serializers.ErrorResponseSerializer,
        },
    )
    @action(
        detail=True,
        methods=["GET"],
    )
    def download(self, request, pk=None):  # pylint: disable=unused-argument, invalid-name
        """
        Return the PDF file in bytes fully signed to download from the signature provider.
        """
        contract = self.get_object()

        if contract.order.state != enums.ORDER_STATE_VALIDATED:
            raise ValidationError(
                "Cannot get contract when an order is not yet validated."
            )

        if not contract.is_fully_signed:
            raise ValidationError(
                "Cannot download a contract when it is not yet fully signed."
            )

        signed_contract_pdf_bytes = contract_utility.get_pdf_bytes_of_contracts(
            signature_backend_references=[contract.signature_backend_reference]
        )

        # it’s your task to seek() it before passing it to FileResponse.
        contract_pdf_bytes_io = io.BytesIO(signed_contract_pdf_bytes[0])
        contract_pdf_bytes_io.seek(0)

        return FileResponse(
            contract_pdf_bytes_io,
            as_attachment=True,
            filename=f"{contract.definition.title}.pdf".replace(" ", "_"),
        )

    @action(
        methods=["GET", "OPTIONS"],
        detail=False,
        url_name="zip-archive",
        url_path=rf"zip-archive/(?P<zip_id>{UUID_REGEX})",
    )
    def get_zip_archive(self, request, zip_id):
        """
        Return the ZIP archive once it has been generated and it exists into storages.

        When the ZIP archive is not ready yet, we will return a response with the status code 404
        until the ZIP is available to be served. Once available, we return the ZIP archive.
        If the paired User UUID and the received ZIP UUID do not match any files in storage,
        it return a response with the status code 404.
        You must add the ZIP id as a payload.
        """

        storage = storages["contracts"]
        zip_archive_name = f"{request.user.id}_{zip_id}.zip"
        zip_archive_exists = storage.exists(zip_archive_name)

        if not zip_archive_exists:
            return Response(status=HTTPStatus.NOT_FOUND)

        if request.method == "GET":
            return FileResponse(
                storage.open(zip_archive_name, mode="rb"),
                as_attachment=True,
                filename=zip_archive_name,
                content_type="application/zip",
            )

        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        methods=["POST"],
        detail=False,
        url_name="generate_zip_archive",
        url_path="zip-archive",
    )
    def generate_zip_archive(self, request, **kwargs):  # pylint: disable=no-self-use, unused-argument,
        """
        This endpoint is exclusive to users that have access rights on a specific organization.

        It triggers the generation of a ZIP archive if the requesting has the correct access rights
        on the organization. If a course product relation UUID is given from key word arguments,
        the user requires to have access to the organization that is attached to the specific
        course product relation object.
        We return in the response the URL for polling the ZIP archive once it has been generated.

        Notes on possible `kwargs` as input parameters :
            - string of an Organization UUID alone
            - string of an CourseProductRelation UUID alone
            - string of both Organization UUID & CourseProductRelation UUID
        """
        serializer = serializers.GenerateSignedContractsZipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not contract_utility.get_signature_backend_references_exists(
            course_product_relation=serializer.validated_data.get(
                "course_product_relation"
            ),
            organization=serializer.validated_data.get("organization"),
            extra_filters={"order__organization__accesses__user_id": request.user.id},
        ):
            raise ValidationError("No zip to generate")

        # Generate here the zip uuid4 to generate ZIP archive for the requesting user
        zip_id = uuid.uuid4()  # ZIP UUID to build the ZIP archive name
        options = {
            "user": request.user.id,
            "organization_id": serializer.data.get("organization_id"),
            "course_product_relation_id": serializer.data.get(
                "course_product_relation_id"
            ),
            "zip": str(zip_id),
        }

        generate_zip_archive_task.delay(options)

        url_base = reverse("contracts-zip-archive", kwargs={"zip_id": str(zip_id)})

        return JsonResponse({"url": url_base}, status=HTTPStatus.ACCEPTED)


class NestedOrganizationContractViewSet(NestedGenericViewSet, GenericContractViewSet):
    """
    Nested Contract Viewset inside organization route.
    It allows to list & retrieve organization's contracts if the user is
    an administrator or an owner of the organization.

    GET /api/courses/<organization_id|organization_code>/contracts/
        Return list of all organization's contracts

    GET /api/courses/<organization_id|organization_code>/contracts/<contract_id>/
        Return an organization's contract if one matches the provided id
    """

    lookup_fields = ["order__organization__pk", "pk"]
    lookup_url_kwargs = ["organization_id", "pk"]

    def _lookup_by_organization_code_or_pk(self):
        """
        Override `lookup_fields` to lookup by organization code or pk according to
        the `organization_id` kwarg is a valid UUID or not.
        """
        try:
            uuid.UUID(self.kwargs["organization_id"])
        except ValueError:
            self.lookup_fields[0] = "order__organization__code__iexact"

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling method handler.
        """
        super().initial(request, *args, **kwargs)
        self._lookup_by_organization_code_or_pk()

    def get_queryset(self):
        """
        Customize the queryset to get only organization's contracts for those user has
        access to.
        """
        queryset = super().get_queryset()

        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        query_filters = {
            "order__organization__accesses__user__username": username,
        }

        return queryset.filter(**query_filters)


class NestedCourseContractViewSet(NestedGenericViewSet, GenericContractViewSet):
    """
    Nested Contract Viewset inside course route.
    It allows to list & retrieve course's contracts if the user is an administrator
    or an owner of the contract's organization.

    GET /api/courses/<course_id|course_code>/contracts/
        Return list of all course's contracts

    GET /api/courses/<course_id|course_code>/contracts/<contract_id>/
        Return a course's contract if one matches the provided id
    """

    lookup_fields = ["order__course__pk", "pk"]
    lookup_url_kwargs = ["course_id", "pk"]

    def _lookup_by_course_code_or_pk(self):
        """
        Override `lookup_fields` to lookup by course code or pk according to
        the `course_id` kwarg is a valid UUID or not.
        """
        try:
            uuid.UUID(self.kwargs["course_id"])
        except ValueError:
            self.lookup_fields[0] = "order__course__code__iexact"

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling method handler.
        """
        super().initial(request, *args, **kwargs)
        self._lookup_by_course_code_or_pk()

    def get_queryset(self):
        """
        Customize the queryset to get only course's contracts for those user has
        access to. By "access", we mean the user is administrator or owner of the
        organization.
        """
        queryset = super().get_queryset()

        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        query_filters = {
            "order__organization__accesses__user__username": username,
        }

        return queryset.filter(**query_filters)


class ContractDefinitionViewset(viewsets.GenericViewSet):
    """
    API views to preview the contract definition for a user

    GET /api/contract_definition/:contract_definition_id/preview_template
        Return the contract definition file in PDF format.
    """

    permission_classes = [permissions.IsAuthenticated]
    queryset = models.ContractDefinition.objects.all()

    @extend_schema(
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            404: serializers.ErrorResponseSerializer,
            422: serializers.ErrorResponseSerializer,
        },
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="preview_template",
    )
    def preview_template(self, request, pk=None):  # pylint: disable=invalid-name, unused-argument
        """
        Return the contract definition in PDF in bytes.
        """
        definition = self.get_object()
        context = contract_definition.generate_document_context(
            contract_definition=definition,
            user=self.request.user,
        )
        contract_definition_pdf_bytes = issuers.generate_document(
            name=definition.name, context=context
        )
        contract_definition_pdf_bytes_io = io.BytesIO(contract_definition_pdf_bytes)
        contract_definition_pdf_bytes_io.seek(0)

        return FileResponse(
            contract_definition_pdf_bytes_io,
            as_attachment=True,
            filename="contract_definition_preview_template.pdf",
        )


class NestedOrderCourseViewSet(NestedGenericViewSet, mixins.ListModelMixin):
    """
    Nested Order Viewset inside Course's routes. It allows to list all users who made
    'validated' orders on a given course. You should add some query parameters to filter
    the list by organization, by product or by course product relation id.

    GET /api/courses/<course_id>/orders/
        Returns every users who made an order on a given course.

    GET /api/courses/<course_id>/orders/?organization_id=<organization_id>>
        Returns every users who made an order on a course from a specific organization.

    GET /api/courses/<course_id>/orders/?product_id=<product_id>
        Returns every users who made an order on the product's course.

    GET /api/courses/<course_id>/orders/?organization_id=<organization_id>&product_id=<product_id>
        Returns every users that is attached to a product's course and an organization.

    GET /api/courses/<course_id>/orders/?course_product_relation_id=<relation_id>
        Returns every users who made order on the course product relation object.
    """

    lookup_fields = ["course__pk", "pk"]
    lookup_url_kwargs = ["course_id", "pk"]
    permission_classes = [permissions.AccessPermission]
    serializer_class = serializers.NestedOrderCourseSerializer
    filterset_class = filters.NestedOrderCourseViewSetFilter
    ordering = ["-created_on"]
    queryset = (
        models.Order.objects.filter(state=enums.ORDER_STATE_VALIDATED)
        .select_related(
            "contract",
            "certificate",
            "course",
            "enrollment",
            "organization",
            "owner",
            "product",
        )
        .distinct()
    )

    def get_queryset(self):
        """Returns the queryset of orders where the user has access on the organization"""
        queryset = super().get_queryset()
        return queryset.filter(organization__accesses__user=self.request.user)


class ActivityLogViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ActivityLog ViewSet
    """

    permission_classes = [permissions.AccessPermission]
    serializer_class = serializers.ActivityLogSerializer

    def get_permissions(self):
        """
        User only needs to be authenticated, except for create action.
        Signatures are checked for create action.
        """
        if self.action == "create":
            permission_classes = [drf_permissions.AllowAny]
        else:
            return super().get_permissions()

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Only return users if a query is provided to filter them.
        """
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        return models.ActivityLog.objects.filter(user__username=username)

    def create(self, request, *args, **kwargs):
        """
        Create a new activity log for allowed clients.
        """
        check_signature(request, "JOANIE_ACTIVITY_LOG_SECRETS")
        return super().create(request, *args, **kwargs)
