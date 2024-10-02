"""Admin context processors."""

from django.conf import settings


def settings_processors(request):
    """Bind settings value to context for admin views purpose."""
    return {
        "ADMIN_BACKOFFICE_URL": settings.JOANIE_BACKOFFICE_BASE_URL,
    }
