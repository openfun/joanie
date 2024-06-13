"""Payment"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
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


def get_country_calendar():
    """
    Instantiate the contract's calendar through `JOANIE_CONTRACT_COUNTRY_CALENDAR` setting.
    """
    try:
        calendar_path = settings.JOANIE_CALENDAR
        return import_string(calendar_path)()
    except (AttributeError, ImportError) as error:
        raise ImproperlyConfigured(
            "Cannot instantiate a calendar. "
            f'`JOANIE_CONTRACT_COUNTRY_CALENDAR="{calendar_path}"` configuration seems not valid. '
            "Check your settings.py"
        ) from error
