"""API for the joanie project."""
from django.core.exceptions import ValidationError as DjangoValidationError

from django_fsm import TransitionNotAllowed
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception.

    For the parameters, see ``exception_handler``
    This code comes from twidi's gist:
    https://gist.github.com/twidi/9d55486c36b6a51bdcb05ce3a763e79f

    Handle TransitionNotAllowed from django_fsm to avoid getting a 500
    """
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "message"):
            detail = exc.message
        elif hasattr(exc, "messages"):
            detail = exc.messages
        exc = DRFValidationError(detail=detail)
    elif isinstance(exc, TransitionNotAllowed):
        detail = str(exc)
        exc = DRFValidationError(detail=detail, code=422)

    return drf_exception_handler(exc, context)
