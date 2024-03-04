"""Joanie Signature application"""

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from joanie.signature.backends import get_signature_backend


class SignatureConfig(AppConfig):
    """Configuration class for the joanie signature app."""

    name = "joanie.signature"
    verbose_name = _("Joanie signature application")

    def ready(self):
        """
        Import JOANIE SIGNATURE BACKEND configuration settings.
        While loading the project, a signature backend is not required
        but if one is activated, it should be correctly configured.
        """
        try:
            backend = get_signature_backend()
        except (AttributeError, ImportError, TypeError) as error:
            raise ImproperlyConfigured(
                "Cannot instantiate a signature backend. "
                "JOANIE_SIGNATURE_BACKEND configuration seems not valid. "
                "Check your settings.py."
            ) from error

        for name in backend.required_settings:
            if getattr(settings, backend.get_setting_name(name), None) is None:
                raise ImproperlyConfigured(
                    f"Required setting {backend.get_setting_name(name)} is not defined."
                )
