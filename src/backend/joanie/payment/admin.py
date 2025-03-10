"""
Payment application admin
"""

from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from admin_auto_filters.filters import AutocompleteFilter

from joanie.core.models import User
from joanie.payment import enums, models


class InvoiceFilter(AutocompleteFilter):
    """Filter on an "invoice" foreign key."""

    title = _("Invoice")
    field_name = "invoice"


class RequiredOwnerFilter(AutocompleteFilter):
    """Filter on an "owner" foreign key."""

    title = _("Owner")
    field_name = "owner"

    def queryset(self, request, queryset):
        """Don't return any results until a value is selected in the filter."""
        if self.value():
            return super().queryset(request, queryset)

        return super().queryset(request, queryset).none()


class RequiredOwnersFilter(AutocompleteFilter):
    """Filter on "owners" ManyToMany field."""

    title = _("Owner")
    field_name = "owners"

    def queryset(self, request, queryset):
        """
        Filter the queryset to include only credit cards where the selected owner
        is in the ManyToMany 'owners' relationship.
        """
        if self.value():
            return super().queryset(request, queryset)

        return super().queryset(request, queryset).none()


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin class for the Invoice model."""

    autocomplete_fields = ["order", "parent"]
    list_display = (
        "reference",
        "created_on",
        "type",
        "recipient_full_name",
        "total",
        "balance",
    )
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
    search_fields = [
        "reference",
        "recipient_address__first_name",
        "recipient_address__last_name",
        "parent__reference",
    ]
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

    def recipient_full_name(self, obj):  # pylint: disable=no-self-use
        """Return the recipient name of the invoice."""
        return obj.recipient_address.full_name

    def children(self, obj):  # pylint: disable=no-self-use
        """Return a list of children."""
        children = obj.children.all()
        if children:
            items = [
                (
                    "<li>"
                    "<a href='"
                    f"{reverse('admin:payment_invoice_change', args=(invoice.id,))}"
                    "'>"
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
                    f"<a href='{reverse('admin:payment_transaction_change', args=(transaction.id,))}'>"  # pylint: disable=line-too-long
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

    autocomplete_fields = ["invoice"]
    list_display = ("reference", "created_on", "total")
    list_filter = [InvoiceFilter]

    def get_readonly_fields(self, request, obj=None):
        """Return readonly fields according if obj exists or not."""
        if obj:
            return "reference", "invoice", "total", "created_on"

        return ()


class CreditCardOwnersInline(admin.TabularInline):
    """
    Facilitate to add owners on creation of a credit card
    """

    model = models.CreditCard.owners.through
    extra = 0


@admin.register(models.CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    """Admin class for the credit card model."""

    autocomplete_fields = ["owners"]
    exclude = [
        "owner",
        "is_main",
    ]  # Hide all deprecated fields on CreditCard Model
    list_display = (
        "get_owner_ownership",
        "title",
        "numbers",
        "expiration_date",
        "get_is_main_ownership",
        "has_token",
        "has_initial_issuer_transaction_identifier",
        "payment_provider",
    )
    list_filter = [RequiredOwnersFilter]
    readonly_fields = ("has_token", "has_initial_issuer_transaction_identifier")
    inlines = [CreditCardOwnersInline]

    def get_queryset(self, request):
        """
        The admin user needs to set an owner in the required filter first. We
        retrieve the owner's pk to use for the ownership filtering for the methods
        `get_is_main_ownership` and `get_owner_ownership`.
        """
        queryset = super().get_queryset(request)
        self.owner_pk = request.GET.get("owners__pk__exact")  # pylint:disable=attribute-defined-outside-init
        return queryset

    @admin.display(boolean=True, description=_("Main"))
    def get_is_main_ownership(self, obj):
        """Return whether the credit card ownership is main for the owner"""
        return obj.ownerships.get(owner__pk=self.owner_pk).is_main

    @admin.display(description=_("Owner"))
    def get_owner_ownership(self, obj):  # pylint:disable=unused-argument
        """
        Returns the list of usernames allowed to use the credit card.
        """
        return User.objects.get(pk=self.owner_pk).username

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

    @staticmethod
    @admin.display(boolean=True)
    def has_initial_issuer_transaction_identifier(credit_card):
        """
        Return the initial issuer transaction identifier
        """
        return credit_card.initial_issuer_transaction_identifier is not None

    @staticmethod
    @admin.display(boolean=True)
    def has_token(credit_card):
        """
        Return the token of the credit card
        """
        return credit_card.token is not None

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        Add instruction to explain that, due to the RequiredOwnersFilter, no results will be
        shown until the view is filtered for a specific owner.
        """
        extra_context = extra_context or {}
        extra_context["subtitle"] = _("To get results, choose an owner on the right")
        return super().changelist_view(request, extra_context=extra_context)
