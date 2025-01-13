"""
API endpoints
"""

import logging
from http import HTTPStatus

from django.db import transaction
from django.http import JsonResponse

from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from joanie.core.models import User
from joanie.payment import exceptions, get_payment_backend, models, serializers

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
    except exceptions.ParseNotificationFailed as error:
        return Response(str(error), status=error.status_code)

    return Response(status=HTTPStatus.OK)


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

        return models.CreditCard.objects.get_cards_for_owner(
            username=username
        ).order_by("-is_main", "-created_on")

    @action(
        methods=["POST"],
        detail=False,
        url_path="tokenize-card",
    )
    def tokenize_card(self, request):
        """
        Tokenize a credit card for a user with payment backend. It returns a form token
        from the payment backend provider.
        """
        payment_backend = get_payment_backend()
        payment_infos = payment_backend.tokenize_card(user=self.request.user)

        return Response(payment_infos, status=HTTPStatus.OK)

    def destroy(self, request, *args, **kwargs):
        """
        Delete the relation between the card and the owner when there are many
        owners on a shared card only if there are no pending payment on the owner's orders.
        If there is only one owner on the card and there are no pending payments we can delete
        the credit card.
        """
        credit_card = self.get_object()
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )

        # Check for pending payments on the credit card for the user
        if credit_card.orders.filter(owner__username=username).exists():
            return JsonResponse(
                {
                    "details": "Cannot delete the credit card, there are still ongoing pending "
                    f"payments for this credit card {credit_card.id}"
                },
                status=HTTPStatus.CONFLICT,
            )

        if credit_card.owners.count() > 1:
            owner = User.objects.get(username=username)
            credit_card.owners.remove(owner)
            return Response(status=HTTPStatus.NO_CONTENT)

        # If this is the last owner, delete the credit card
        super().destroy(request, *args, **kwargs)
        return Response(status=HTTPStatus.NO_CONTENT)
