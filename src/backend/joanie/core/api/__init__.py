"""API for the joanie project."""

from http import HTTPStatus

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as drf_exception_handler
from viewflow.fsm import TransitionNotAllowed


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception.

    For the parameters, see ``exception_handler``
    This code comes from twidi's gist:
    https://gist.github.com/twidi/9d55486c36b6a51bdcb05ce3a763e79f

    Handle TransitionNotAllowed from viewflow to avoid getting a 500
    """
    detail = None
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
        exc = DRFValidationError(detail=detail, code=HTTPStatus.UNPROCESSABLE_ENTITY)

    return drf_exception_handler(exc, context)
