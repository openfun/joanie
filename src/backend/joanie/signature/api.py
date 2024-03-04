"""
API endpoint for Signature
"""

import logging
from http import HTTPStatus

from django.db import transaction

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from joanie.signature.backends import get_signature_backend

logger = logging.getLogger(__name__)


@api_view(["POST"])
@transaction.atomic()
def webhook_signature(request: Request):
    """
    The webhook called by the signature provider when a file has been signed/refused.
    """
    signature_backend = get_signature_backend()
    signature_backend.handle_notification(request)

    return Response(status=HTTPStatus.OK)
