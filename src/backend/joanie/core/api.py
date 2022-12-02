"""
API endpoints
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse

from rest_framework import mixins, pagination, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from joanie.core import models
from joanie.core.enums import ORDER_STATE_PENDING
from joanie.payment import get_payment_backend
from joanie.payment.models import ProformaInvoice

from ..core import filters
from ..core.models import User
from ..payment.models import CreditCard
from . import serializers


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception.

    For the parameters, see ``exception_handler``
    This code comes from twidi's gist:
    https://gist.github.com/twidi/9d55486c36b6a51bdcb05ce3a763e79f
    """
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "message"):
            detail = exc.message
        elif hasattr(exc, "messages"):
            detail = exc.messages

        exc = DRFValidationError(detail=detail)

    return drf_exception_handler(exc, context)


class Pagination(pagination.PageNumberPagination):
    """Pagination to display no more than 100 objects per page sorted by creation date."""

    ordering = "-created_on"
    page_size = 100


class CourseViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """API ViewSet for all interactions with courses."""

    lookup_field = "code"
    permission_classes = [permissions.AllowAny]
    queryset = models.Course.objects.select_related("organization").all()
    serializer_class = serializers.CourseSerializer

    def get_serializer_context(self):
        """
        Provide username to the authenticated user (if one is authenticated)
        to the `CourseSerializer`
        """
        context = super().get_serializer_context()

        if self.request.user.username:
            context.update({"username": self.request.user.username})

        return context


class CourseRunViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """API ViewSet for all interactions with course runs."""

    lookup_field = "id"
    permissions_classes = [permissions.AllowAny]
    queryset = models.CourseRun.objects.filter(is_listed=True)
    serializer_class = serializers.CourseRunSerializer


class ProductViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """API ViewSet for all interactions with products."""

    lookup_field = "id"
    permissions_classes = [permissions.AllowAny]
    filterset_class = filters.ProductViewSetFilter
    queryset = (
        models.Product.objects.filter(courses__isnull=False)
        .distinct()
        .select_related("certificate_definition")
    )
    serializer_class = serializers.ProductSerializer

    def get_serializer_context(self):
        """
        Provide username to the authenticated user (if one is authenticated)
        and course code to the `ProductSerializer`
        """
        context = super().get_serializer_context()

        if self.request.user.username:
            context.update({"username": self.request.user.username})

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

    def get_queryset(self):
        """Custom queryset to limit to orders owned by the logged-in user."""
        user = User.update_or_create_from_request_user(request_user=self.request.user)
        return user.enrollments.all().select_related("course_run")

    def perform_create(self, serializer):
        """Force the enrollment's "owner" field to the logged-in user."""
        user = User.update_or_create_from_request_user(request_user=self.request.user)
        serializer.save(user=user)


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
        user = User.update_or_create_from_request_user(request_user=self.request.user)
        return user.orders.all().select_related("owner", "product", "certificate")

    def perform_create(self, serializer):
        """Force the order's "owner" field to the logged-in user."""
        owner = User.update_or_create_from_request_user(request_user=self.request.user)
        serializer.save(owner=owner)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Try to create an order and a related payment if the payment is fee."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        product = serializer.validated_data.get("product")
        course = serializer.validated_data.get("course")
        billing_address = serializer.initial_data.get("billing_address")

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
        username = request.user.username
        payment_id = request.data.get("payment_id")

        try:
            order = models.Order.objects.get(pk=pk, owner__username=username)
        except models.Order.DoesNotExist:
            return Response(
                f'No order found with id "{pk}" owned by {username}.', status=404
            )

        if order.state != ORDER_STATE_PENDING:
            return Response("Cannot abort a not pending order.", status=403)

        if payment_id:
            payment_backend = get_payment_backend()
            payment_backend.abort_payment(payment_id)

        order.cancel()

        return Response(status=204)

    @action(detail=True, methods=["GET"])
    def proforma_invoice(
        self, request, pk=None
    ):  # pylint: disable=no-self-use, invalid-name
        """
        Retrieve a pro forma invoice through its reference if it is related to
        the order instance and owned by the authenticated user.
        """
        reference = request.query_params.get("reference")

        if reference is None:
            return Response({"reference": "This parameter is required."}, status=400)

        try:
            proforma_invoice = ProformaInvoice.objects.get(
                reference=reference,
                order__id=pk,
                order__owner__username=request.user.username,
            )
        except ProformaInvoice.DoesNotExist:
            return Response(
                (
                    f"No pro forma invoice found for order {pk} "
                    f"with reference {reference}."
                ),
                status=404,
            )

        response = HttpResponse(
            proforma_invoice.document, content_type="application/pdf", status=200
        )
        response[
            "Content-Disposition"
        ] = f"attachment; filename={proforma_invoice.reference}.pdf;"

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
        user = User.update_or_create_from_request_user(request_user=self.request.user)
        return user.addresses.all()

    def perform_create(self, serializer):
        """Create a new address for user authenticated"""
        user = User.update_or_create_from_request_user(request_user=self.request.user)
        serializer.save(owner=user)


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

    def get_queryset(self):
        """
        Custom queryset to get user certificates
        """
        user = User.update_or_create_from_request_user(request_user=self.request.user)
        return models.Certificate.objects.filter(order__owner=user)

    @action(detail=True, methods=["GET"])
    def download(self, request, pk=None):  # pylint: disable=no-self-use, invalid-name
        """
        Retrieve a certificate through its id if it is owned by the authenticated user.
        """
        try:
            certificate = models.Certificate.objects.get(
                pk=pk,
                order__owner__username=request.user.username,
            )
        except models.Certificate.DoesNotExist:
            return Response(
                {"detail": f"No certificate found with id {pk}."}, status=404
            )

        response = HttpResponse(
            certificate.document, content_type="application/pdf", status=200
        )

        response["Content-Disposition"] = f"attachment; filename={pk}.pdf;"

        return response
