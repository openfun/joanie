"""Views of the ``core`` app of the Joanie project."""
from django.conf import settings
from django.contrib.sites.models import Site
from django.views.generic.base import RedirectView, TemplateView

from ..core.factories import OrderFactory


class DebugMailSuccessPayment(TemplateView):
    """Debug View to check the layout of the success payment email"""

    def get_context_data(self, **kwargs):
        """Generates sample datas to have a valid debug email"""
        site = Site.objects.get_current()
        order = OrderFactory()
        context = super().get_context_data(**kwargs)
        context["title"] = "👨‍💻Development email preview"
        context["email"] = order.owner.email
        context["fullname"] = order.owner.get_full_name() or order.owner.username
        context["product"] = order.product
        context["site"] = {
            "name": site.name,
            "url": "https://" + site.domain,
        }

        return context


class DebugMailSuccessPaymentViewHtml(DebugMailSuccessPayment):
    """Debug View to check the layout of the success payment email
    in html format."""

    template_name = "mail/html/order_validated.html"


class DebugMailSuccessPaymentViewTxt(DebugMailSuccessPayment):
    """Debug View to check the layout of the success payment email
    in text format"""

    template_name = "mail/text/order_validated.txt"


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
