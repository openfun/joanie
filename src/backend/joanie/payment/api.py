"""
API endpoints
"""
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import permission_classes
from .models import CreditCard


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

    PUT /api/credit-cards/<credit_card_uid> with expected data:
        - title: str
        - is_main?: bool

    DELETE /api/credit-cards/<credit_card_uid>
        Delete the selected credit card
    """

    lookup_field = "uid"
    serializer_class = serializers.CreditCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Custom queryset to get user's credit cards"""
        user = User.objects.get_or_create(username=self.request.user.username)[0]
        return user.credit_cards.all()
