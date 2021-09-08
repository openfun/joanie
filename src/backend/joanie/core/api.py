"""
API endpoints
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import generics, mixins, pagination, permissions, status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from joanie.core import models

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
    queryset = models.Course.objects.all()
    serializer_class = serializers.CourseSerializer


# pylint: disable=too-many-ancestors
class EnrollmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """API ViewSet for all interactions with enrollments."""

    lookup_field = "uid"
    pagination_class = Pagination
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.EnrollmentSerializer

    def get_queryset(self):
        """Custom queryset to limit to orders owned by the logged-in user."""
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        return user.enrollments.all().select_related("course_run")

    def perform_create(self, serializer):
        """Force the enrollment's "owner" field to the logged-in user."""
        username = self.request.user.username
        user = models.User.objects.get_or_create(username=username)[0]
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
        - product: product uid (product must be associated to the course. Otherwise,
          a 400 error is returned)
        Return new order just created
    """

    lookup_field = "uid"
    pagination_class = Pagination
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        """Custom queryset to limit to orders owned by the logged-in user."""
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        return (
            user.orders.all()
            .select_related("owner", "product")
            .prefetch_related("enrollments__course_run")
        )

    def perform_create(self, serializer):
        """Force the order's "owner" field to the logged-in user."""
        username = self.request.user.username
        owner = models.User.objects.get_or_create(username=username)[0]
        serializer.save(owner=owner)


class AddressView(generics.ListAPIView):
    """
    API view allows to get all addresses or create or update a new one for a user.

    GET /api/addresses/
        Return list of all addresses for a user

    POST /api/addresses/ with expected data:
        - address: str
        - city: str
        - country: str, country code
        - fullname: str, recipient fullname
        - main?: bool, if True set address as main
        - postcode: str
        - title: str, address title
        Return new address just created

    PUT /api/addresses/<address_id>/ with expected data:
        - address: str
        - city: str
        - country: str, country code
        - fullname: str, recipient fullname
        - main?: bool, if True set address as main
        - postcode: str
        - title: str, address title
        Return address just updated

    DELETE /api/addresses/<address_id>/
        Delete selected address
    """

    serializer_class = serializers.AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    instance_field = "address_uid"

    def get_queryset(self):
        """Custom queryset to get user addresses"""
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        return user.addresses.all()

    def get_instance(self, **kwargs):
        """Get address instance"""
        return get_object_or_404(models.Address, uid=kwargs[self.instance_field])

    def put(self, request, **kwargs):
        """Update address selected with new data"""
        if self.instance_field and self.instance_field in kwargs:
            obj = self.get_instance(**kwargs)
            # User authenticated has to be the address owner
            if obj.owner.username == self.request.user.username:
                serializer = self.serializer_class(instance=obj, data=request.data)
                if not serializer.is_valid():
                    return Response(
                        {"errors": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer.save()
                return Response({"data": serializer.data})
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Create a new address for user authenticated"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        serializer.save(owner=user)
        return Response(status=status.HTTP_201_CREATED, data={"data": serializer.data})

    def delete(self, request, **kwargs):
        """Delete address selected"""
        obj = self.get_instance(**kwargs)
        # User authenticated has to be the address owner
        if obj.owner.username == self.request.user.username:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)
