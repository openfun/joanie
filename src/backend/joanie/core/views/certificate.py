"""Certificate views for the Joanie core app."""

import base64

from django.contrib.sites.models import Site
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from joanie.core import models
from joanie.core.enums import DEGREE
from joanie.core.utils import issuers


class CertificateVerificationView(TemplateView):
    """A view to verify that a certificate is authentic."""

    template_name = "certificate/verify.html"

    def get_context_data(self, **kwargs):
        """
        Try to get the certificate from the certificate id url parameter. If it exists
        bind the certificate context and the generated PDF to the context.
        """
        context = super().get_context_data(**kwargs)

        certificate_id = kwargs.get("certificate_id")
        certificate = get_object_or_404(
            models.Certificate,
            id=certificate_id,
            certificate_definition__template=DEGREE,
        )

        certificate_context = certificate.get_document_context()
        document = issuers.generate_document(
            name=certificate.certificate_definition.template,
            context=certificate_context,
        )
        site = Site.objects.get_current()

        context.update(
            {
                "certificate_context": certificate_context,
                "base64_pdf": base64.b64encode(document).decode("utf-8"),
                "site": {
                    "name": site.name,
                    "hostname": f"https://{site.domain}",
                },
            }
        )

        return context
