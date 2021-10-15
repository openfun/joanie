"""
Payment application enums declaration
"""

from django.utils.translation import gettext_lazy as _

# Invoice types
INVOICE_TYPE_INVOICE = "invoice"
INVOICE_TYPE_CREDIT_NOTE = "credit_note"

INVOICE_TYPES = (
    # - An invoice with positive amount
    (INVOICE_TYPE_INVOICE, _("Invoice")),
    # - An invoice with negative amount
    (INVOICE_TYPE_CREDIT_NOTE, _("Credit note")),
)


# Invoice states
INVOICE_STATE_UNPAID = "unpaid"
INVOICE_STATE_PAID = "paid"
INVOICE_STATE_REFUNDED = "refunded"

INVOICE_STATES = (
    # - UNPAID : Invoice is not fully paid
    (INVOICE_STATE_UNPAID, _("Unpaid")),
    # - PAID : Invoice is fully paid
    (INVOICE_STATE_PAID, _("Paid")),
    # - REFUNDED : invoice balances are equal to zero
    (INVOICE_STATE_REFUNDED, _("Refunded")),
)
