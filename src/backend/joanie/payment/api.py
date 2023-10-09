"""
API endpoints
"""
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import exceptions, get_payment_backend, models, serializers

logger = logging.getLogger(__name__)


@api_view(["POST"])
@transaction.atomic()
def webhook(request):
    """
    The webhook called by payment provider
    when a payment has been created/updated/refunded...
    """

    payment_backend = get_payment_backend()
    try:
        payment_backend.handle_notification(request)
    except (exceptions.ParseNotificationFailed, ValidationError) as exception:
        logger.error("Cannot handle payment notification", exc_info=exception)
        return Response(str(exception), status=getattr(exception, "status_code", 500))

    return Response(status=200)


# pylint: disable=too-many-ancestors
class CreditCardViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API views allows to get all credit cards, update or delete one
    for the authenticated user.

    GET /api/credit-cards/
        Return the list of all credit cards owned by the authenticated user

    PUT /api/credit-cards/<credit_card_id> with expected data:
        - title: str
        - is_main?: bool

    DELETE /api/credit-cards/<credit_card_id>
        Delete the selected credit card
    """

    lookup_field = "id"
    serializer_class = serializers.CreditCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Custom queryset to get user's credit cards"""
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        return models.CreditCard.objects.filter(owner__username=username)
