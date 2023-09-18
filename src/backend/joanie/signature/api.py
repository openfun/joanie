"""
API endpoints for Signature
"""
import logging

from django.db import transaction

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .backends import get_signature_backend

logger = logging.getLogger(__name__)


@api_view(["POST"])
@transaction.atomic()
def webhook_signature(request):
    """
    The webhook called by the signature provider
    when a document has been signed or refused.
    """
    signature_backend = get_signature_backend()
    try:
        signature_backend.handle_notification(request)
    except exceptions.ParseNotificationFailed as error:
        return Response(str(error), status=error.status_code)

    return Response(status=200)
