"""
Declare and configure models for the payment part
"""

import logging
from decimal import Decimal as D

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from babel.numbers import get_currency_symbol
from parler.utils import get_language_settings
from parler.utils.context import switch_language

from joanie.core.models.base import BaseModel
from joanie.core.utils import merge_dict
from joanie.payment import enums as payment_enums
from joanie.payment import get_payment_backend
from joanie.payment.exceptions import PaymentProviderAPIException

User = get_user_model()
logger = logging.getLogger(__name__)


class Invoice(BaseModel):
    """
    Invoice model is an informative accounting element related to an order
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
        to="core.Order",
        verbose_name=_("order"),
        related_name="invoices",
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )
    total = models.DecimalField(
        _("total"),
        decimal_places=2,
        max_digits=9,
        null=False,
        blank=False,
    )
    recipient_address = models.ForeignKey(
        to="core.Address",
        verbose_name=_("invoice address"),
        related_name="invoices",
        on_delete=models.RESTRICT,
    )
    localized_context = models.JSONField(
        _("context"),
        help_text=_("Localized data that needs to be frozen on invoice creation"),
        editable=False,
        encoder=DjangoJSONEncoder,
    )

    class Meta:
        db_table = "joanie_invoice"
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(parent__isnull=True) & models.Q(total__gte=0)
                    | models.Q(parent__isnull=False)
                ),
                name="main_invoice_should_have_a_positive_amount",
                violation_error_message="Credit note should have a parent invoice.",
            ),
            models.UniqueConstraint(
                condition=models.Q(parent__isnull=True),
                fields=["order"],
                name="only_one_invoice_without_parent_per_order",
                violation_error_message="A main invoice already exists for this order.",
            ),
        ]

    def __str__(self):
        types = dict(payment_enums.INVOICE_TYPES)
        return f"{types[self.type]} {self.reference}"

    @property
    def state(self) -> str:
        """
        Process the state of the invoice
        """
        if self.balance >= 0:
            if self.invoiced_balance == 0 and self.transactions_balance == 0:
                return payment_enums.INVOICE_STATE_REFUNDED

            return payment_enums.INVOICE_STATE_PAID

        return payment_enums.INVOICE_STATE_UNPAID

    @property
    def type(self):
        """
        Return the invoice type according to its total amount.
        If total amount is positive, invoice type is "invoice"
        otherwise it's "credit_note"
        """
        if self.total < 0:
            return payment_enums.INVOICE_TYPE_CREDIT_NOTE

        return payment_enums.INVOICE_TYPE_INVOICE

    @property
    def transactions_balance(self):
        """
        Process the transactions balance.

        First we retrieve all transactions registered for the current invoice
        and its children. Then we sum all transactions amount.
        """

        amount = Transaction.objects.filter(
            Q(invoice__in=self.children.all()) | Q(invoice=self)
        ).aggregate(total=models.Sum("total"))["total"] or D(0.00)

        return amount

    @property
    def invoiced_balance(self):
        """
        Process the invoiced amount.

        First we retrieve all invoice's children
        then we sum all invoice amount.
        """
        invoices = [
            self,
            *self.children.only("total").all(),
        ]
        amount = sum(invoice.total for invoice in invoices)

        return amount

    @property
    def balance(self):
        """
        Difference between transaction balance and invoiced balance.
        """
        # - Compute the balance
        return self.transactions_balance - self.invoiced_balance

    def _set_localized_context(self):
        """
        Update or create the invoice context for all languages.

        In order to save space, we want to generate related document only on
        demand. Furthermore, we need to store product description to prevent
        inconsistency in case of product would be updated. That's why we store
        a product information for all active language into the invoice,
        then we are able to generate invoice document with consistent data
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
                            "description": related_product.description,  # pylint: disable=no-member,line-too-long
                        }
                    }
                }

        self.localized_context = context

    def get_document_context(self, language_code=None):
        """
        Build the invoice document context for the given language.
        If no language_code is provided, we use the active language.
        """
        language_settings = get_language_settings(language_code or get_language())

        vat = D(settings.JOANIE_VAT)
        vat_amount = self.total * vat / 100
        net_amount = self.total - vat_amount
        currency = get_currency_symbol(settings.DEFAULT_CURRENCY)

        base_context = {
            "metadata": {
                "issued_on": self.updated_on,
                "reference": self.reference,
                "type": self.type,
            },
            "order": {
                "amount": {
                    "currency": currency,
                    "subtotal": str(net_amount),
                    "total": str(self.total),
                    "vat_amount": str(vat_amount),
                    "vat": str(vat),
                },
                "company": settings.JOANIE_INVOICE_COMPANY_CONTEXT,
                "customer": {
                    "address": self.recipient_address.full_address,
                    "name": self.recipient_address.full_name,
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
        First ensure that the invoice is at least linked to an order or
        a parent but not both.
        Then, if the invoice is linked to a parent, `recipient_address`
        with its parent values.
        Finally, if the invoice is a credit note, ensure its total amount is
        not greater than its parent total amount.
        """

        if self.parent and self.parent.parent is not None:
            raise ValidationError(
                _("invoice cannot have as parent another invoice which is a child.")
            )

        if self.parent:
            self.recipient_address = self.parent.recipient_address

        if self.type == payment_enums.INVOICE_TYPE_CREDIT_NOTE:
            if self.parent and self.total * -1 > self.parent.invoiced_balance:
                raise ValidationError(
                    _(
                        "Credit note amount cannot be greater than its related "
                        "invoice invoiced balance."
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

        super().save(*args, **kwargs)


class Transaction(BaseModel):
    """
    Transaction model represents financial transactions
    (debit, credit) related to an invoice.
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

    invoice = models.ForeignKey(
        to=Invoice,
        verbose_name=_("invoice"),
        related_name="transactions",
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )

    total = models.DecimalField(
        _("total"),
        decimal_places=2,
        max_digits=9,
    )

    class Meta:
        db_table = "joanie_transaction"
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        transaction_type = "Credit" if self.total < 0 else "Debit"
        return f"{transaction_type} transaction ({self.total})"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


class CreditCardManager(models.Manager):
    """Custom manager for `CreditCard` model"""

    def get_card_for_owner(self, pk, username):
        """
        Retrieve a credit card for a given owner. If no such card exists, a
        CreditCard.DoesNotExist is raised.
        """
        payment_provider = get_payment_backend()

        return self.get(
            pk=pk, owners__username=username, payment_provider=payment_provider.name
        )

    def get_cards_for_owner(self, username):
        """
        Retrieve all the credit cards for a given owner that are tokenized by the
        active payment provider
        """
        payment_provider = get_payment_backend()

        return self.filter(
            owners__username=username, payment_provider=payment_provider.name
        )


class CreditCardOwnership(BaseModel):
    """
    CreditCardOwnership model allows to define the ownership of a user and a credit card,
    finally it defines when it's the main one.
    """

    owner = models.ForeignKey(
        to=User, on_delete=models.CASCADE, related_name="credit_card_ownerships"
    )
    credit_card = models.ForeignKey(
        to="payment.CreditCard", on_delete=models.CASCADE, related_name="ownerships"
    )
    is_main = models.BooleanField(_("main"), default=False)

    class Meta:
        db_table = "joanie_credit_card_ownership"
        verbose_name = "credit_card_ownership"
        verbose_name_plural = "credit card ownernships"
        ordering = ["-created_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "is_main"],
                condition=models.Q(is_main=True),
                name="unique_main_credit_card_per_user",
            ),
            models.UniqueConstraint(
                fields=["credit_card", "owner"], name="unique_credit_card_ownership"
            ),
        ]

    def clean(self, *args, **kwargs):
        """
        First if this is the user's first credit card, we enforce `is_main` to True.
        Else if we are promoting a credit card as main, we demote the existing main credit card
        Finally we prevent to demote the main credit card directly.
        """
        if not self.__class__.objects.filter(owner=self.owner).exists():
            self.is_main = True
        elif self.is_main:
            self.__class__.objects.filter(owner=self.owner, is_main=True).update(
                is_main=False
            )
        elif (
            self.created_on
            and not self.is_main
            and self.__class__.objects.filter(
                owner=self.owner, credit_card=self.credit_card, is_main=True
            ).exists()
        ):
            raise ValidationError(_("Demote a main credit card is forbidden"))

        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


class CreditCard(BaseModel):
    """
    Credit card model stores credit card information in order to allow
    one click payment.
    """

    objects = CreditCardManager()
    token = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        editable=False,
        null=False,
    )
    initial_issuer_transaction_identifier = models.CharField(
        _("initial issuer transaction identifier"),
        max_length=50,
        null=True,
        blank=True,
        editable=False,
    )
    title = models.CharField(_("title"), max_length=100, null=True, blank=True)
    brand = models.CharField(_("brand"), max_length=40, null=True, blank=True)
    expiration_month = models.PositiveSmallIntegerField(
        _("expiration month"), validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    expiration_year = models.PositiveSmallIntegerField(_("expiration year"))
    last_numbers = models.CharField(_("last 4 numbers"), max_length=4)
    # Deprecated
    owner = models.ForeignKey(
        to=User,
        verbose_name=_("owner"),
        related_name="credit_cards",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    owners = models.ManyToManyField(
        to=User,
        verbose_name=_("owners"),
        related_name="payment_cards",
        through="CreditCardOwnership",
        through_fields=("credit_card", "owner"),
    )
    is_main = models.BooleanField(_("main"), default=False)  # Deprecated
    payment_provider = models.CharField(
        _("payment provider"), max_length=50, null=True, blank=True
    )

    class Meta:
        db_table = "joanie_credit_card"
        verbose_name = "credit card"
        verbose_name_plural = "credit cards"
        ordering = ["-created_on"]

    def add_owner(self, owner):
        """
        Add new owner to the credit card owners field through the `CreditCardOwnership` model to
        enforce the validation logic (through the clean() method) for the field `is_main`
        of ownership each time it's saved.
        """
        CreditCardOwnership.objects.create(
            owner=owner,
            credit_card=self,
        )

    def clean(self):
        """
        It's required to have a `payment_provider` value, because we add credit card through a
        payment provider only.
        """
        if not self.payment_provider:
            raise ValidationError(_("Payment provider field cannot be None."))
        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


@receiver(models.signals.post_delete, sender=CreditCard)
# pylint: disable=unused-argument
def credit_card_post_delete_receiver(sender, instance, *args, **kwargs):
    """
    Post delete receiver method for credit card model.

    Each time we delete a credit card from database,
    we have also to delete it from the payment provider
    """
    try:
        payment_backend = get_payment_backend()
        payment_backend.delete_credit_card(instance)
    except PaymentProviderAPIException as exception:
        logger.error(
            "An error occurred while deleting a credit card token from payment provider.",
            exc_info=exception,
            extra={
                "context": {
                    "paymentMethodToken": instance.token,
                }
            },
        )
