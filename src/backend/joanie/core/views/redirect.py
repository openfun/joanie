"""Redirect views of the `core`app."""

from django.conf import settings
from django.views.generic.base import RedirectView


class BackOfficeRedirectView(RedirectView):
    """
    Redirect to the next.js backoffice application
    with the path caught in the redirect url
    """

    permanent = True
    query_string = False
    pattern_name = None
    http_method_names = ["get"]

    def get_redirect_url(self, *args, **kwargs):
        """
        Redirect to the backoffice pathname caught in the url
        """
        return f"{settings.JOANIE_BACKOFFICE_BASE_URL}/{self.kwargs['path']}"
