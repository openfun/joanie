"""Newsletter client utils."""

from django.conf import settings
from django.utils.module_loading import import_string


def get_newsletter_client():
    """
    Get the newsletter client.
    """
    return (
        import_string(settings.JOANIE_NEWSLETTER_CLIENT)
        if settings.JOANIE_NEWSLETTER_CLIENT
        else None
    )
