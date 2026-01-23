"""
API utilities for the Joanie core app.
"""

from django.conf import settings
from django.http import HttpRequest


def get_authenticated_username(request: HttpRequest) -> str:
    """
    Get the authenticated username from the request.
    """
    user_id_claim = settings.SIMPLE_JWT["USER_ID_CLAIM"]
    return request.auth[user_id_claim] if request.auth else request.user.username
