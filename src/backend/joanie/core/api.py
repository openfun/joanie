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
from joanie.payment import backends

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

        Optional data :
            - credit_card: dict, contains credit card data
                name: str, credit card name chosen by user
                card_number: str, credit card number e.g. 1111222233334444
                cryptogram: str, credit card cryptogram e.g. 222
                expiration_date: str, credit card expiration date e.g. '09/21' ('%M%y')
                save: bool, to register credit card (to a future oneclick payment)
            }
            or
            - credit_card: dict, contains credit card uid to get credit card for oneclick payment
                id: uid

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
        """Force the order's "owner" field to the logged-in user and proceed to payment"""
        username = self.request.user.username
        owner = models.User.objects.get_or_create(username=username)[0]
        order = serializer.save(owner=owner)
        if order.price and self.request.data.get("credit_card"):
            order.proceed_to_payment(**self.request.data["credit_card"])


class AddressView(generics.ListAPIView):
    """
    API view allows to get all addresses or create or update a new one for a user.

    GET /api/addresses/
        Return list of all addresses for a user

    POST /api/addresses/ with expected data:
        - name: str, address name
        - address: str
        - postcode: str
        - city: str
        - country: str, country code
        Return new address just created

    PUT /api/addresses/<address_id>/ with expected data:
        - name: str, address name
        - address: str
        - postcode: str
        - city: str
        - country: str, country code
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


class CreditCardView(generics.ListAPIView):
    """
    API view allows to get all credit cards or update or create a new one for a user.

    GET /api/credit_cards/
        Return list of all user credit cards saved
        [
            {
                'id': uid,
                'name': str,
                'last_numbers': str, four last digits
                'expiration_date': date, only "month/year" e.g. "09/22"
                'main': bool,
            },
        ]

    POST /api/credit_cards/ allows to register a new credit card with expected data:
        - name: str, user can name his/her credit card
        - card_number: str, credit card number e.g. 1111222233334444
        - cryptogram: str, credit card cryptogram e.g. 222
        - expiration_date: str, only "month/year" e.g. "09/22" is expected
        - main: bool,

    PUT /api/credit_cards/<credit_card_uid>/ allows to modify credit card name and main flag
    with expected data:
        - name: str,
        - main: bool,

    DELETE /api/credit_cards/<credit_card_uid>/ allows to remove credit card
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CreditCardModelSerializer
    instance_field = "credit_card_uid"

    def get_instance(self, **kwargs):
        """Get credit card instance"""
        return get_object_or_404(models.CreditCard, uid=kwargs[self.instance_field])

    def get_queryset(self):
        """Custom queryset to get user credit cards"""
        user = models.User.objects.get_or_create(username=self.request.user.username)[0]
        return user.creditcards.all()

    def post(self, request):
        """Register a new credit card to future oneclick payment.
        Call payment backend, save token returned on credit card object and
        use uid returned to set uid of credit card object.
        """
        serializer = serializers.CreditCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = models.User.objects.get_or_create(username=request.user.username)[0]
        payment_backend = backends.get_backend()
        try:
            uid, token = payment_backend.register_credit_card(
                request.data.get("card_number"),
                request.data.get("cryptogram"),
                request.data.get("expiration_date"),
            )
        except backends.PaymentNetworkError as err:
            return Response(
                status=status.HTTP_504_GATEWAY_TIMEOUT, data={"errors": err.messages}
            )
        except backends.PaymentServiceError as err:
            return Response(
                status=status.HTTP_400_BAD_REQUEST, data={"errors": err.messages}
            )

        credit_card = user.creditcards.create(
            name=request.data.get("name"),
            uid=uid,
            token=token,
            last_numbers=request.data.get("card_number")[-4:],
            expiration_date=backends.compute_expiration_date(
                request.data.get("expiration_date")
            ),
            main=request.data.get("main"),
        )
        serializer = serializers.CreditCardModelSerializer(credit_card)
        return Response(status=status.HTTP_201_CREATED, data=serializer.data)

    def put(self, request, **kwargs):
        """Update credit card selected with new data.
        Only update credit card name and main flag."""
        if self.instance_field and self.instance_field in kwargs:
            obj = self.get_instance(**kwargs)
            # User authenticated has to be the credit card owner
            if obj.owner.username == request.user.username:
                serializer = self.serializer_class(obj, data=request.data)
                if not serializer.is_valid():
                    return Response(
                        {"errors": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer.save()
                return Response(serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, **kwargs):
        """Delete credit card selected. Call payment backend to unregister credit card."""
        if self.instance_field and self.instance_field in kwargs:
            obj = self.get_instance(**kwargs)
            # User authenticated has to be the credit card owner
            if obj.owner.username == request.user.username:
                payment_backend = backends.get_backend()
                try:
                    removed = payment_backend.remove_credit_card(obj)
                except backends.PaymentNetworkError as err:
                    return Response(
                        status=status.HTTP_504_GATEWAY_TIMEOUT,
                        data={"errors": err.messages},
                    )
                except backends.PaymentServiceError as err:
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST,
                        data={"errors": err.messages},
                    )
                if removed:
                    obj.delete()
                    return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)
