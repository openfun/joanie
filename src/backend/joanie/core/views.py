"""Views of the ``core`` app of the Joanie project."""
import base64

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.views.generic.base import RedirectView, TemplateView

from joanie.core import factories
from joanie.core.enums import CERTIFICATE, DEGREE
from joanie.core.models import Certificate
from joanie.core.utils import issuers


class DebugMailSuccessPayment(TemplateView):
    """Debug View to check the layout of the success payment email"""

    def get_context_data(self, **kwargs):
        """Generates sample datas to have a valid debug email"""
        site = Site.objects.get_current()
        order = factories.OrderFactory()
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


class DebugCertificateDefinitionTemplateView(TemplateView):
    """
    Debug View to check the layout of certificate definition templates
    """

    type = None

    # pylint: disable=invalid-name, unused-argument
    def retrieve_certificate_from_pk(self, pk, site):
        """
        Retrieve a certificate from its pk and its certificate definition template
        and generate its document
        """
        certificate = Certificate.objects.get(
            pk=pk,
            certificate_definition__template=self.type,
        )

        document = issuers.generate_document(
            name=certificate.definition.template,
            context=certificate.get_document_context(),
        )

        return document

    # pylint: disable=unused-argument
    def generate_certificate(self, site):
        """
        Generate an enrollment certificate document with hardcoded organization,
        course, enrollment and certificate definition to prevent to create a lot of
        objects in the database.
        """
        organization = factories.OrganizationFactory(
            code=f"DEV_{self.type.upper()}_ORGANIZATION",
        )

        course = factories.CourseFactory(
            code=f"DEV_{self.type.upper()}_COURSE",
            organizations=[organization],
        )

        enrollment = factories.EnrollmentFactory(
            course_run__course=course,
        )

        definition = factories.CertificateDefinitionFactory.create(
            name=f"DEV_{self.type.upper()}_DEFINITION",
            template=self.type,
        )

        certificate = factories.EnrollmentCertificateFactory.create(
            certificate_definition=definition,
            organization=organization,
            enrollment=enrollment,
        )

        document = issuers.generate_document(
            name=definition.template, context=certificate.get_document_context()
        )

        return document

    def get_context_data(self, **kwargs):
        """
        Generates sample datas to have a valid debug certificate/degree definition.

        If the request contains a pk query parameter, we retrieve the certificate
        from its pk and its certificate definition template otherwise we generate on the
        fly a certificate document.
        """
        context = super().get_context_data()
        current_site = get_current_site(self.request)

        # pylint: disable=invalid-name
        if pk := self.request.GET.get("pk"):
            document = self.retrieve_certificate_from_pk(pk, current_site)
        else:
            document = self.generate_certificate(current_site)

        context.update(
            **{
                "base64_pdf": base64.b64encode(document).decode("ascii"),
            }
        )

        return context


class DebugCertificateTemplateView(DebugCertificateDefinitionTemplateView):
    """
    Debug view to check the layout of "certificate" template
    """

    template_name = "debug/pdf_viewer.html"
    type = CERTIFICATE


class DebugDegreeTemplateView(DebugCertificateDefinitionTemplateView):
    """
    Debug view to check the layout of "degree" template
    """

    template_name = "debug/pdf_viewer.html"
    type = DEGREE


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
