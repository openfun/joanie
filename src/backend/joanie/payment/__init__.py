"""Payment"""

from django.conf import settings
from django.utils.module_loading import import_string


def get_payment_backend():
    """Instantiate a payment backend through `JOANIE_PAYMENT_BACKEND` setting."""
    try:
        backend = settings.JOANIE_PAYMENT_BACKEND.get("backend")
        configuration = settings.JOANIE_PAYMENT_BACKEND.get("configuration")
        return import_string(backend)(configuration)
    except (AttributeError, ImportError, TypeError) as error:
        raise ValueError(
            "Cannot instantiate a payment backend. "
            "JOANIE_PAYMENT_BACKEND configuration seems not valid. "
            "Check your settings.py."
        ) from error
