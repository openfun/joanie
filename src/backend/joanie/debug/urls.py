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
    DebugMailAllInstallmentPaidViewHtml,
    DebugMailAllInstallmentPaidViewTxt,
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
        "__debug__/mail/installment-paid-html",
        DebugMailSuccessInstallmentPaidViewHtml.as_view(),
        name="debug.mail.installment_paid_html",
    ),
    path(
        "__debug__/mail/installment-paid-txt",
        DebugMailSuccessInstallmentPaidViewTxt.as_view(),
        name="debug.mail.installment_paid_txt",
    ),
    path(
        "__debug__/mail/installments_fully_paid_html",
        DebugMailAllInstallmentPaidViewHtml.as_view(),
        name="debug.mail.installments_fully_paid_html",
    ),
    path(
        "__debug__/mail/installments_fully_paid_txt",
        DebugMailAllInstallmentPaidViewTxt.as_view(),
        name="debug.mail.installments_fully_paid_txt",
    ),
]
