"""Get Signature Backend"""
from django.conf import settings
from django.utils.module_loading import import_string


def get_signature_backend():
    """Instantiate a signature backend through `JOANIE_SIGNATURE_BACKEND` settings."""
    signature_backend = getattr(settings, "JOANIE_SIGNATURE_BACKEND", None)
    return import_string(signature_backend)()
