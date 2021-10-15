"""
Payment application admin
"""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from . import enums, models


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin class for the invoice model."""

    list_display = ("type", "reference", "recipient_name", "total", "balance")
    readonly_fields = (
        "balance",
        "children",
        "created_on",
        "invoiced_balance",
        "state",
        "transactions",
        "transactions_balance",
        "type",
        "updated_on",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "total",
                    (
                        "order",
                        "parent",
                    ),
                    "recipient_name",
                    "recipient_address",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "type",
                    ("created_on", "updated_on"),
                    "state",
                    (
                        "balance",
                        "transactions_balance",
                        "invoiced_balance",
                    ),
                    "children",
                    "transactions",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """Return readonly fields."""

        if obj:
            return self.readonly_fields + (
                "total",
                "order",
                "parent",
                "recipient_name",
                "recipient_address",
            )
        return self.readonly_fields

    def type(self, obj):  # pylint: disable=no-self-use
        """Return human-readable type of the invoice."""
        types = dict(enums.INVOICE_TYPES)
        return types[obj.type]

    def state(self, obj):  # pylint: disable=no-self-use
        """Return human-readable state of the invoice."""
        states = dict(enums.INVOICE_STATES)
        return states[obj.state]

    def children(self, obj):  # pylint: disable=no-self-use
        """Return a list of children."""
        children = obj.children.all()
        if children:
            items = [
                (
                    "<li>"
                    f"<a href='{reverse('admin:payment_invoice_change', args=(invoice.id,),)}'>"
                    f"{str(invoice)} ({invoice.total})"
                    "</a>"
                    "</li>"
                )
                for invoice in children
            ]
            return format_html(f"<ul style='margin: 0'>{''.join(items)}</ul>")
        return "-"

    def transactions(self, obj):  # pylint: disable=no-self-use
        """Return a list of transactions linked to the invoice."""
        transactions = obj.transactions.all()
        if transactions:
            items = [
                (
                    "<li>"
                    f"<a href='{reverse('admin:payment_transaction_change', args=(transaction.id,),)}'>"  # noqa pylint: disable=line-too-long
                    f"{str(transaction)}"
                    "</a>"
                    "</li>"
                )
                for transaction in transactions
            ]
            return format_html(f"<ul style='margin: 0'>{''.join(items)}</ul>")
        return "-"


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin class for the transaction model."""

    list_display = ("reference", "total", "created_on")

    def get_readonly_fields(self, request, obj=None):
        """Return readonly fields according if obj exists or not."""
        if obj:
            return "reference", "invoice", "total", "created_on"

        return ()


@admin.register(models.CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    """Admin class for the credit card model."""

    list_display = ("owner", "title", "numbers", "expiration_date", "is_main")

    @staticmethod
    def numbers(credit_card):
        """
        Return credit_card.last_numbers into a human-readable format
        """
        return f"XXXX XXXX XXXX {credit_card.last_numbers}"

    @staticmethod
    def expiration_date(credit_card):
        """
        Retrieve a human-readable expiration date from
        expiration_month and expiration_year
        """

        return f"{credit_card.expiration_month:02d}/{credit_card.expiration_year:02d}"
