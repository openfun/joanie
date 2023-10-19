"""
Client API endpoints
"""
# pylint: disable=too-many-lines

import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from rest_framework import mixins, pagination
from rest_framework import permissions as drf_permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from joanie.core import enums, filters, models, permissions, serializers
from joanie.core.api.base import NestedGenericViewSet
from joanie.payment.models import Invoice

# pylint: disable=too-many-ancestors


class Pagination(pagination.PageNumberPagination):
    """Pagination to display no more than 100 objects per page sorted by creation date."""

    ordering = "-created_on"
    max_page_size = 100
    page_size_query_param = "page_size"


class CourseRunViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """API ViewSet for all interactions with course runs."""

    lookup_field = "id"
    pagination_class = Pagination
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

    @method_decorator(cache_page(settings.JOANIE_ANONYMOUS_API_DEFAULT_CACHE_TTL))
    @method_decorator(vary_on_headers("Accept-Language"))
    def retrieve_through_nested_course(self, request, *args, **kwargs):
        """
        Retrieve relation through its course id and product id should be cached
        per language.
        """
        return super().retrieve(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        The retrieve action is used to get a single course product relation.
        The response is cached per language.
        """
        if self.kwargs.get("course_id"):
            return self.retrieve_through_nested_course(request, *args, **kwargs)

        return super().retrieve(request, *args, **kwargs)

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
        if self.action == "retrieve" and self.kwargs.get("course_id"):
            permission_classes = [drf_permissions.AllowAny]
        else:
            return super().get_permissions()

        return [permission() for permission in permission_classes]


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
                        "product", "product__contract_definition"
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
        instance = serializer.save(user=self.request.user)
        instance.set()

    def perform_update(self, serializer):
        """
        Synchronize the enrollment with the LMS.
        """
        instance = serializer.save()
        instance.set()


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
            "certificate", "contract", "course", "owner", "product"
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
            course_relation = product.course_relations.get(course=course)
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
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        course_code = serializer.initial_data.get("course")

        enrollment = serializer.validated_data.get("enrollment")
        product = serializer.validated_data.get("product")

        # Retrieve course instance from the provided course code
        if course_code:
            try:
                course = models.Course.objects.get(code=course_code)
            except models.Course.DoesNotExist:
                return Response(
                    {"course": ["Course with code {course_code} does not exist."]},
                    status=400,
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
                    status=400,
                )
            course = enrollment.course_run.course

        # Force the organization field
        if not serializer.validated_data.get("organization"):
            serializer.validated_data[
                "organization"
            ] = self._get_organization_with_least_active_orders(
                product, course, enrollment
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
                status=400,
            )

        # Else return the fresh new order
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["PATCH"])
    def submit(
        self, request, pk=None
    ):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """
        Submit a draft order if the conditions are filled
        """
        serializer = self.get_serializer(data=request.data)
        billing_address = serializer.initial_data.get("billing_address")
        credit_card_id = serializer.initial_data.get("credit_card_id")
        order = self.get_object()

        return Response(
            {"payment_info": order.submit(billing_address, credit_card_id, request)},
            status=201,
        )

    @action(detail=True, methods=["POST"])
    def abort(
        self, request, pk=None
    ):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """Change the state of the order to pending"""
        payment_id = request.data.get("payment_id")

        order = self.get_object()

        if order.state == enums.ORDER_STATE_VALIDATED:
            return Response("Cannot abort a validated order.", status=422)

        order.pending(payment_id)

        return Response(status=204)

    @action(detail=True, methods=["POST"])
    def cancel(
        self, request, pk=None
    ):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """Change the state of the order to cancelled"""
        order = self.get_object()

        if order.state == enums.ORDER_STATE_VALIDATED:
            return Response("Cannot cancel a validated order.", status=422)

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

    @action(detail=True, methods=["PUT"])
    def validate(
        self, request, pk=None
    ):  # pylint: disable=no-self-use, invalid-name, unused-argument
        """
        Validate the order
        """
        order = self.get_object()
        order.validate()
        return Response(status=200)


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
                Q(order__owner__username=username)
                | Q(enrollment__user__username=username),
                pk=pk,
            )
        except models.Certificate.DoesNotExist:
            return Response(
                {"detail": f"No certificate found with id {pk}."}, status=404
            )

        (document, _) = certificate.generate_document()

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
    pagination_class = Pagination
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
    pagination_class = Pagination
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ContractSerializer
    filterset_class = filters.ContractViewSetFilter
    ordering = ["-signed_on", "-created_on"]
    queryset = models.Contract.objects.all().select_related(
        "definition",
        "order__organization",
        "order__course",
        "order__owner",
        "order__product",
    )


class ContractViewSet(GenericContractViewSet):
    """
    Contract Viewset to list & retrieve contracts owned by the authenticated user.

    GET /api/contracts/
        Return list of all contracts owned by the logged-in user.

    GET /api/contracts/<contract_id>/
        Return a contract if one matches the provided id,
        and it is owned by the logged-in user.
    """

    lookup_field = "pk"

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
            "order__organization__accesses__role__in": [enums.OWNER, enums.ADMIN],
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
            "order__organization__accesses__role__in": [enums.OWNER, enums.ADMIN],
        }

        return queryset.filter(**query_filters)
