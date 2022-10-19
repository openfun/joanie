"""
Declare and configure models for the payment part
"""
from decimal import Decimal as D

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from babel.numbers import get_currency_symbol
from djmoney.models.fields import MoneyField
from djmoney.money import Money
from howard.issuers import InvoiceDocument
from parler.utils import get_language_settings
from parler.utils.context import switch_language

from joanie.core.models import BaseModel, Order
from joanie.core.utils import merge_dict

from . import enums as payment_enums
from . import get_payment_backend

User = get_user_model()


class ProformaInvoice(BaseModel):
    """
    ProformaInvoice model is an informative accounting element related to an order
    """

    parent = models.ForeignKey(
        to="self",
        on_delete=models.RESTRICT,
        related_name="children",
        verbose_name="parent",
        blank=True,
        null=True,
    )
    reference = models.CharField(
        db_index=True,
        editable=False,
        max_length=40,
        unique=True,
    )
    order = models.ForeignKey(
        to=Order,
        verbose_name=_("order"),
        related_name="proforma_invoices",
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )
    total = MoneyField(
        _("total"),
        max_digits=9,
        decimal_places=2,
        default_currency=settings.DEFAULT_CURRENCY,
        null=False,
        blank=False,
    )
    recipient_name = models.CharField(
        _("proforma invoice recipient"), max_length=40, null=False, blank=False
    )
    recipient_address = models.TextField(
        _("proforma invoice address"), max_length=255, null=False, blank=False
    )
    localized_context = models.JSONField(
        _("context"),
        help_text=_(
            "Localized data that needs to be frozen on pro forma invoice creation"
        ),
        editable=False,
    )

    class Meta:
        db_table = "joanie_proforma_invoice"
        verbose_name = _("Pro forma invoice")
        verbose_name_plural = _("Pro forma invoices")
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(parent__isnull=True) & models.Q(total__gte=0)
                    | models.Q(parent__isnull=False)
                ),
                name="main_proforma_invoice_should_have_a_positive_amount",
            ),
            models.UniqueConstraint(
                condition=models.Q(parent__isnull=True),
                fields=["order"],
                name="only_one_proforma_invoice_without_parent_per_order",
            ),
        ]

    def __str__(self):
        types = dict(payment_enums.INVOICE_TYPES)
        return f"Pro forma {types[self.type]} {self.reference}"

    @property
    def state(self):
        """
        Process the state of the pro forma invoice
        """
        if self.balance.amount >= 0:
            if (
                self.invoiced_balance.amount == 0
                and self.transactions_balance.amount == 0
            ):
                return payment_enums.INVOICE_STATE_REFUNDED

            return payment_enums.INVOICE_STATE_PAID

        return payment_enums.INVOICE_STATE_UNPAID

    @property
    def document(self):
        """
        Get the document related to the pro forma invoice instance;
        """
        document = InvoiceDocument(context_query=self.get_document_context())
        return document.create(persist=False)

    @property
    def type(self):
        """
        Return the pro forma invoice type according to its total amount.
        If total amount is positive, pro forma invoice type is "invoice"
        otherwise it's "credit_note"
        """
        if self.total.amount < 0:  # pylint: disable=no-member
            return payment_enums.INVOICE_TYPE_CREDIT_NOTE

        return payment_enums.INVOICE_TYPE_INVOICE

    @property
    def transactions_balance(self):
        """
        Process the transactions balance.

        First we retrieve all transactions registered for the current pro forma invoice
        and its children. Then we sum all transactions amount.
        """

        amount = Transaction.objects.filter(
            Q(proforma_invoice__in=self.children.all()) | Q(proforma_invoice=self)
        ).aggregate(total=models.Sum("total"))["total"] or D(0.00)

        return Money(amount, self.total.currency)  # pylint: disable=no-member

    @property
    def invoiced_balance(self):
        """
        Process the invoiced amount.

        First we retrieve all pro forma invoice's children
        then we sum all pro forma invoice amount.
        """
        proforma_invoices = [
            self,
            *self.children.only("total", "total_currency").all(),
        ]
        amount = sum(invoice.total.amount for invoice in proforma_invoices)

        return Money(amount, self.total.currency)  # pylint: disable=no-member

    @property
    def balance(self):
        """
        Difference between transaction balance and invoiced balance.
        """
        # - Compute the balance
        return self.transactions_balance - self.invoiced_balance

    def _set_localized_context(self):
        """
        Update or create the pro forma invoice context for all languages.

        In order to save space, we want to generate related document only on
        demand. Furthermore, we need to store product description to prevent
        inconsistency in case of product would be updated. That's why we store
        a product information for all active language into the pro forma invoice,
        then we are able to generate pro forma invoice document with consistent data
        only on demand.

        Saving is left to the caller.
        """

        context = {}
        related_product = self.order.product
        for language, __ in settings.LANGUAGES:
            with switch_language(related_product, language):
                context[language] = {
                    "order": {
                        "product": {
                            "name": related_product.title,  # pylint: disable=no-member
                            "description": related_product.description,  # noqa pylint: disable=no-member,line-too-long
                        }
                    }
                }

        self.localized_context = context

    def get_document_context(self, language_code=None):
        """
        Build the pro forma invoice document context for the given language.
        If no language_code is provided, we use the active language.
        """
        language_settings = get_language_settings(language_code or get_language())

        vat = D(settings.JOANIE_VAT)
        total_amount = self.total.amount  # pylint: disable=no-member
        vat_amount = total_amount * vat / 100
        net_amount = total_amount - vat_amount
        currency = get_currency_symbol(
            self.total.currency.code  # pylint: disable=no-member
        )

        base_context = {
            "metadata": {
                "issued_on": str(self.updated_on),
                "reference": self.reference,
                "type": self.type,
            },
            "order": {
                "amount": {
                    "currency": currency,
                    "subtotal": str(net_amount),
                    "total": str(total_amount),
                    "vat_amount": str(vat_amount),
                    "vat": str(vat),
                },
                "company": settings.JOANIE_INVOICE_COMPANY_CONTEXT,
                "customer": {
                    "address": self.recipient_address,
                    "name": self.recipient_name,
                },
                "seller": {
                    "address": settings.JOANIE_INVOICE_SELLER_ADDRESS,
                },
            },
        }

        try:
            localized_context = self.localized_context[language_settings["code"]]
        except KeyError:
            # - Otherwise use the first entry of the localized context
            localized_context = list(self.localized_context.values())[0]

        return merge_dict(base_context, localized_context)

    def normalize_reference(self):
        """
        Generate a normalized reference related to the date
        and the related order
        """
        order_uid_fragment = str(self.order.id).split("-", maxsplit=1)[0]
        timestamp = int(timezone.now().timestamp() * 1_000)  # Time in milliseconds

        return f"{order_uid_fragment}-{timestamp}"

    def clean(self):
        """
        First ensure that the pro forma invoice is at least linked to an order or
        a parent but not both.
        Then, if the pro forma invoice is linked to a parent, set `recipient_name` and
        `recipient_address` with its parent values.
        Finally, if the pro forma invoice is a credit note, ensure its total amount is
        not greater than its parent total amount.
        """

        if self.parent and self.parent.parent is not None:
            raise ValidationError(
                _(
                    "Pro forma invoice cannot have as parent "
                    "another pro forma invoice which is a child."
                )
            )

        if self.parent:
            self.recipient_name = self.parent.recipient_name
            self.recipient_address = self.parent.recipient_address

        if self.type == payment_enums.INVOICE_TYPE_CREDIT_NOTE:
            if not self.parent:
                raise ValidationError(
                    _("Credit note must have a parent pro forma invoice.")
                )

            if (
                self.total.amount * -1  # pylint: disable=no-member
                > self.parent.invoiced_balance.amount  # pylint: disable=no-member
            ):
                raise ValidationError(
                    _(
                        "Credit note amount cannot be greater than its related "
                        "pro forma invoice invoiced balance."
                    )
                )

        if self.created_on is None:
            self.reference = self.normalize_reference()

        return super().clean()

    def save(self, *args, **kwargs):
        """
        Enforce validation each time an instance is saved.

        On creation, we also create a context for each active languages.
        """

        self.full_clean()

        is_new = self.created_on is None

        if is_new:
            self._set_localized_context()

        models.Model.save(self, *args, **kwargs)


class Transaction(BaseModel):
    """
    Transaction model represents financial transactions
    (debit, credit) related to a pro forma invoice.
    """

    reference = models.CharField(
        help_text=_("Reference to identify transaction from external platform"),
        db_index=True,
        max_length=40,
        null=True,
        blank=True,
        editable=False,
        unique=True,
    )

    proforma_invoice = models.ForeignKey(
        to=ProformaInvoice,
        verbose_name=_("proforma invoice"),
        related_name="transactions",
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )

    total = MoneyField(
        _("total"),
        max_digits=9,
        decimal_places=2,
        default_currency=settings.DEFAULT_CURRENCY,
    )

    class Meta:
        db_table = "joanie_transaction"
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        transaction_type = (
            "Credit" if self.total.amount < 0 else "Debit"  # pylint: disable=no-member
        )
        return f"{transaction_type} transaction ({self.total})"


class CreditCard(BaseModel):
    """
    Credit card model stores credit card information in order to allow
    one click payment.
    """

    token = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        editable=False,
        null=False,
    )
    title = models.CharField(_("title"), max_length=100, null=True, blank=True)
    brand = models.CharField(_("brand"), max_length=40, null=True, blank=True)
    expiration_month = models.PositiveSmallIntegerField(
        _("expiration month"), validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    expiration_year = models.PositiveSmallIntegerField(_("expiration year"))
    last_numbers = models.CharField(_("last 4 numbers"), max_length=4)
    owner = models.ForeignKey(
        to=User,
        verbose_name=_("owner"),
        related_name="credit_cards",
        on_delete=models.CASCADE,
    )
    is_main = models.BooleanField(_("main"), default=False)

    class Meta:
        db_table = "joanie_credit_card"
        verbose_name = "credit card"
        verbose_name_plural = "credit cards"
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(is_main=True),
                fields=["owner"],
                name="unique_main_credit_card_per_user",
            )
        ]

    def clean(self):
        """
        First if this is the user's first credit card, we enforce is_main to True.
        Else if we are promoting an credit card as main, we demote the existing main credit card
        Finally prevent to demote the main credit card directly.
        """
        if not self.owner.credit_cards.exists():
            self.is_main = True
        elif self.is_main is True:
            self.owner.credit_cards.filter(is_main=True).update(is_main=False)
        elif (
            self.created_on
            and self.is_main is False
            and self.owner.credit_cards.filter(is_main=True, pk=self.pk).exists()
        ):
            raise ValidationError(_("Demote a main credit card is forbidden"))

        return super().clean()


@receiver(models.signals.post_delete, sender=CreditCard)
# pylint: disable=unused-argument
def credit_card_post_delete_receiver(sender, instance, *args, **kwargs):
    """
    Post delete receiver method for credit card model.

    Each time we delete a credit card from database,
    we have also to delete it from the payment provider
    """
    payment_backend = get_payment_backend()
    payment_backend.delete_credit_card(instance)
