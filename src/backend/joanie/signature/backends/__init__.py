"""Signature"""
from django.conf import settings
from django.utils.module_loading import import_string


def get_signature_backend():
    """Instantiate a signature backend through `JOANIE_SIGNATURE_BACKEND` setting."""
    try:
        backend = settings.JOANIE_SIGNATURE_BACKEND.get("backend")
        configuration = settings.JOANIE_SIGNATURE_BACKEND.get("configuration")
        return import_string(backend)(configuration)
    except (AttributeError, ImportError, TypeError) as error:
        raise ValueError(
            "Cannot instantiate a signature backend. "
            "JOANIE_SIGNATURE_BACKEND configuration seems not valid. "
            "Check your settings.py."
        ) from error
