"""
Client API endpoints
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from rest_framework import mixins, pagination
from rest_framework import permissions as drf_permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from joanie.core import enums, filters, models, permissions, serializers
from joanie.payment import get_payment_backend
from joanie.payment.models import CreditCard, Invoice


class Pagination(pagination.PageNumberPagination):
    """Pagination to display no more than 100 objects per page sorted by creation date."""

    ordering = "-created_on"
    max_page_size = 100
    page_size_query_param = "page_size"


class CourseRunViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """API ViewSet for all interactions with course runs."""

    lookup_field = "id"
    permissions_classes = [drf_permissions.AllowAny]
    queryset = models.CourseRun.objects.filter(is_listed=True).select_related("course")
    serializer_class = serializers.CourseRunSerializer


class ProductViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """API ViewSet for all interactions with products."""

    lookup_field = "id"
    permissions_classes = [drf_permissions.AllowAny]
    filterset_class = filters.ProductViewSetFilter
    queryset = models.Product.objects.all()
    serializer_class = serializers.ProductSerializer

    def filter_queryset(self, queryset):
        """
        Custom queryset to limit to products actually related to the course given in querystring.
        """
        queryset = super().filter_queryset(queryset)

        if self.action == "retrieve":
            try:
                course_code = self.request.query_params["course"]
            except KeyError as exc:
                raise DRFValidationError(
                    {
                        "course": _(
                            "You must specify a course code to get product details."
                        )
                    }
                ) from exc

            queryset = queryset.filter(
                course_relations__course__code=course_code,
                course_relations__organizations__isnull=False,
            )
        else:
            queryset = queryset.filter(course_relations__isnull=False)

        return queryset.select_related("certificate_definition").distinct()

    def get_serializer_context(self):
        """
        Provide course code to the `ProductSerializer`
        """
        context = super().get_serializer_context()

        if course := self.request.query_params.get("course"):
            context.update({"course_code": course})

        return context


# pylint: disable=too-many-ancestors
class EnrollmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """API ViewSet for all interactions with enrollments."""

    lookup_field = "id"
    pagination_class = Pagination
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.EnrollmentSerializer
    filterset_class = filters.EnrollmentViewSetFilter

    def get_queryset(self):
        """Custom queryset to limit to orders owned by the logged-in user."""
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        return models.Enrollment.objects.filter(user__username=username).select_related(
            "course_run__course"
        )

    def perform_create(self, serializer):
        """Force the enrollment's "owner" field to the logged-in user."""
        serializer.save(user=self.request.user)


# pylint: disable=too-many-ancestors
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
    """

    lookup_field = "pk"
    pagination_class = Pagination
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
            "owner", "product", "certificate", "course"
        )

    def perform_create(self, serializer):
        """Force the order's "owner" field to the logged-in user."""
        serializer.save(owner=self.request.user)

    def _get_organization_with_least_active_orders(self, product, course):
        """
        Return the organization with the least not canceled order count
        for a given product and course.
        """
        order_count = Count(
            "order",
            filter=Q(
                Q(order__product=product, order__course=course),
                ~Q(order__state=enums.ORDER_STATE_CANCELED),
            ),
        )

        try:
            course_relation = product.course_relations.get(course=course)
        except models.CourseProductRelation.DoesNotExist:
            return None

        try:
            organizations = (
                course_relation.organizations.annotate(order_count=order_count)
                .order_by("order_count")
                .first()
            )
        except models.Organization.DoesNotExist:
            return None

        return organizations

    # pylint: disable=too-many-return-statements
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Try to create an order and a related payment if the payment is fee."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        product = serializer.validated_data.get("product")
        course_code = serializer.initial_data.get("course")
        billing_address = serializer.initial_data.get("billing_address")

        # Retrieve course instance from the provided course code
        if not course_code:
            return Response({"course": ["This field is required."]}, status=400)

        try:
            course = models.Course.objects.get(code=course_code)
        except models.Course.DoesNotExist:
            return Response(
                {"course": ["Course with code {course_code} does not exist."]},
                status=400,
            )
        serializer.validated_data["course"] = course

        # Populate organization field if it is not set
        if not serializer.validated_data.get("organization"):
            organization = self._get_organization_with_least_active_orders(
                product, course
            )
            serializer.validated_data["organization"] = organization

        # If product is not free, we have to create a payment.
        # To create one, a billing address is mandatory
        if product.price.amount > 0 and not billing_address:
            return Response({"billing_address": "This field is required."}, status=400)

        # - Validate data then create an order
        try:
            self.perform_create(serializer)
        except (DRFValidationError, IntegrityError):
            return Response(
                (
                    f"Cannot create order related to the product {product.id} "
                    f"and course {course.code}"
                ),
                status=400,
            )

        # Once order has been created, if product is not free, create a payment
        if product.price.amount > 0:
            order = serializer.instance
            payment_backend = get_payment_backend()
            credit_card_id = serializer.initial_data.get("credit_card_id")

            # if payment in one click
            if credit_card_id:
                try:
                    credit_card = CreditCard.objects.get(
                        owner=order.owner, id=credit_card_id
                    )
                    payment_info = payment_backend.create_one_click_payment(
                        request=request,
                        order=order,
                        billing_address=billing_address,
                        credit_card_token=credit_card.token,
                    )
                except (CreditCard.DoesNotExist, NotImplementedError):
                    pass
            else:
                payment_info = payment_backend.create_payment(
                    request=request, order=order, billing_address=billing_address
                )

            # Return the fresh new order with payment_info
            return Response(
                {**serializer.data, "payment_info": payment_info}, status=201
            )

        # Else return the fresh new order
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["POST"])
    def abort(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name
        """Abort a pending order and the related payment if there is one."""
        username = request.auth["username"] if request.auth else request.user.username
        payment_id = request.data.get("payment_id")

        try:
            order = models.Order.objects.get(pk=pk, owner__username=username)
        except models.Order.DoesNotExist:
            return Response(
                f'No order found with id "{pk}" owned by {username}.', status=404
            )

        if order.state != enums.ORDER_STATE_PENDING:
            return Response("Cannot abort a not pending order.", status=403)

        if payment_id:
            payment_backend = get_payment_backend()
            payment_backend.abort_payment(payment_id)

        order.cancel()

        return Response(status=204)

    @action(detail=True, methods=["GET"])
    def invoice(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name
        """
        Retrieve an invoice through its reference if it is related to
        the order instance and owned by the authenticated user.
        """
        reference = request.query_params.get("reference")

        if reference is None:
            return Response({"reference": "This parameter is required."}, status=400)

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
                status=404,
            )

        response = HttpResponse(
            invoice.document, content_type="application/pdf", status=200
        )
        response[
            "Content-Disposition"
        ] = f"attachment; filename={invoice.reference}.pdf;"

        return response


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
        return models.Address.objects.filter(owner__username=username)

    def perform_create(self, serializer):
        """Create a new address for user authenticated"""
        serializer.save(owner=self.request.user)


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
    pagination_class = Pagination
    serializer_class = serializers.CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Custom queryset to get user certificates
        """
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        return models.Certificate.objects.filter(
            order__owner__username=username
        ).select_related(
            "certificate_definition", "order__course", "order__organization"
        )

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name
        """
        Retrieve a certificate through its id if it is owned by the authenticated user.
        """
        username = request.auth["username"] if request.auth else request.user.username
        try:
            certificate = models.Certificate.objects.get(
                pk=pk,
                order__owner__username=username,
            )
        except models.Certificate.DoesNotExist:
            return Response(
                {"detail": f"No certificate found with id {pk}."}, status=404
            )

        document = certificate.document

        if not document:
            return Response(
                {"detail": f"Unable to generate certificate {pk}."}, status=422
            )

        response = HttpResponse(document, content_type="application/pdf", status=200)

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
    pagination_class = Pagination
    permission_classes = [permissions.AccessPermission]
    serializer_class = serializers.OrganizationSerializer

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


class OrganizationAccessViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
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

    lookup_field = "pk"
    pagination_class = Pagination
    permission_classes = [permissions.AccessPermission]
    queryset = models.OrganizationAccess.objects.all()
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
    viewsets.GenericViewSet,
):
    """
    API ViewSet for all interactions with course accesses.

    GET /api/course/<course_id>/accesses/:<course_access_id>
        Return list of all course accesses related to the logged-in user or one
        course access if an id is provided.

    POST /api/<course_id>/accesses/ with expected data:
        - user: str
        - role: str [owner|admin|member]
        Return newly created course access

    PUT /api/<course_id>/accesses/<course_access_id>/ with expected data:
        - role: str [owner|admin|member]
        Return updated course access

    PATCH /api/<course_id>/accesses/<course_access_id>/ with expected data:
        - role: str [owner|admin|member]
        Return partially updated course access

    DELETE /api/<course_id>/accesses/<course_access_id>/
        Delete targeted course access
    """

    lookup_field = "pk"
    pagination_class = Pagination
    permission_classes = [permissions.AccessPermission]
    queryset = models.CourseAccess.objects.all()
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
