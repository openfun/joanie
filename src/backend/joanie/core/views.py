"""Views of the ``core`` app of the Joanie project."""
from django.views.generic.base import TemplateView

from ..core.factories import OrderFactory


class DebugMailSuccessPayment(TemplateView):
    """Debug View to check the layout of the success payment email"""

    def get_context_data(self, **kwargs):
        """Generates sample datas to have a valid debug email"""
        order = OrderFactory()
        context = super().get_context_data(**kwargs)
        context["email"] = order.owner.email
        context["username"] = order.owner.username
        context["product"] = order.product

        return context


class DebugMailSuccessPaymentViewHtml(DebugMailSuccessPayment):
    """Debug View to check the layout of the success payment email
    in html format."""

    template_name = "mail/html/purchase_order.html"


class DebugMailSuccessPaymentViewTxt(DebugMailSuccessPayment):
    """Debug View to check the layout of the success payment email
    in text format"""

    template_name = "mail/text/purchase_order.txt"
