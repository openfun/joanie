"""
URL patterns for Debug views to preview template (certificate, degree, invoice, or a contract
definition) which is enable when settings.DEBUG is True exclusively.
"""

from django.urls import path

from joanie.debug.views import (
    DebugCertificateTemplateView,
    DebugContractTemplateView,
    DebugDegreeTemplateView,
    DebugInvoiceTemplateView,
    DebugMailSuccessInstallmentPaidViewHtml,
    DebugMailSuccessInstallmentPaidViewTxt,
    DebugMailSuccessPaymentViewHtml,
    DebugMailSuccessPaymentViewTxt,
    DebugPaymentTemplateView,
)

urlpatterns = [
    path(
        "__debug__/mail/order_validated_html",
        DebugMailSuccessPaymentViewHtml.as_view(),
        name="debug.mail.order_validated_html",
    ),
    path(
        "__debug__/mail/order_validated_txt",
        DebugMailSuccessPaymentViewTxt.as_view(),
        name="debug.mail.order_validated_txt",
    ),
    path(
        "__debug__/pdf-templates/certificate",
        DebugCertificateTemplateView.as_view(),
        name="debug.certificate_definition.certificate",
    ),
    path(
        "__debug__/pdf-templates/degree",
        DebugDegreeTemplateView.as_view(),
        name="debug.certificate_definition.degree",
    ),
    path(
        "__debug__/pdf-templates/contract",
        DebugContractTemplateView.as_view(),
        name="debug.contract.definition",
    ),
    path(
        "__debug__/pdf-templates/invoice",
        DebugInvoiceTemplateView.as_view(),
        name="debug.invoice_template.invoice",
    ),
    path(
        "__debug__/payment",
        DebugPaymentTemplateView.as_view(),
        name="debug.payment_template",
    ),
    path(
        "__debug__/mail/installment_paid_html",
        DebugMailSuccessInstallmentPaidViewHtml.as_view(),
        name="debug.mail.installment_paid_html",
    ),
    path(
        "__debug__/mail/installment_paid_txt",
        DebugMailSuccessInstallmentPaidViewTxt.as_view(),
        name="debug.mail.installment_paid_txt",
    ),
]
