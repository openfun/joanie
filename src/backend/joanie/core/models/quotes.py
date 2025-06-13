"""
Declare and configure the models for Joanie's quotes
"""

import textwrap

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

import markdown

from joanie.core import enums
from joanie.core.models.base import BaseModel, DocumentImage


class QuoteDefinition(BaseModel):
    """
    Quote definition describes the template and markdown to generate quotes.
    """

    class Meta:
        db_table = "joanie_quote_definition"
        verbose_name = _("Quote definition")
        verbose_name_plural = _("Quote definitions")

    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    body = models.TextField(_("body"), blank=True)
    language = models.CharField(
        max_length=10,
        choices=lazy(lambda: settings.LANGUAGES, tuple)(),
        verbose_name=_("language"),
        help_text=_("Language of the contract definition"),
    )
    name = models.CharField(
        _("template name"),
        max_length=255,
        choices=enums.QUOTE_NAME_CHOICES,
        default=enums.QUOTE_DEFAULT,
    )
    images = models.ManyToManyField(
        to=DocumentImage,
        verbose_name=_("images"),
        related_name="quotes",
        editable=False,
        blank=True,
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_body_in_html(self):
        """Return the body in html format."""
        if not self.body:
            return ""
        return markdown.markdown(textwrap.dedent(self.body))


class Quote(BaseModel):
    """
    Quote represents and records the user quote issued as part of a batch order.
    """

    class Meta:
        db_table = "joanie_batch_order_quote"
        verbose_name = _("batch order quote")
        verbose_name_plural = _("batch order quotes")
        constraints = [
            models.CheckConstraint(
                check=~(
                    models.Q(organization_signed_on__isnull=True)
                    & models.Q(buyer_signed_on__isnull=False)
                ),
                name="organization_must_sign_before_buyer",
                violation_error_message=(
                    "Organization must sign quote before the buyer."
                ),
            ),
            models.CheckConstraint(
                check=~(
                    models.Q(has_purchase_order_received=True)
                    & models.Q(buyer_signed_on__isnull=True)
                ),
                name="both_parties_must_sign_before_purchase_order_accepted",
                violation_error_message=(
                    "Both parties must sign quote before confirming the purchase order."
                ),
            ),
            models.CheckConstraint(
                check=~(
                    models.Q(organization_signed_on__isnull=False)
                    & models.Q(context=None)
                ),
                name="The quote requires a context",
                violation_error_message=(
                    "You must generate the quote context before signing the quote."
                ),
            ),
        ]

    batch_order = models.OneToOneField(
        to="core.batchorder",
        verbose_name=_("Batch order"),
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        blank=True,
    )
    definition = models.ForeignKey(
        to=QuoteDefinition,
        verbose_name=_("Quote definition"),
        related_name="quotes",
        on_delete=models.RESTRICT,
        editable=False,
    )
    context = models.JSONField(
        _("context"),
        blank=True,
        help_text=_("Localized data snapshot of the quote generated"),
        editable=False,
        null=True,
        encoder=DjangoJSONEncoder,
    )
    # Quote signature will be done manually for now
    # The business logic wants the organization to sign before the buyer
    organization_signed_on = models.DateTimeField(
        _("Date and time organization signed on"), null=True, blank=True, editable=False
    )
    buyer_signed_on = models.DateTimeField(
        _("Date and time buyer signed on"), null=True, blank=True, editable=False
    )
    has_purchase_order_received = models.BooleanField(
        verbose_name=_("has received the purchase order to confirm the payment"),
        editable=False,
        default=False,
        help_text=_("Quote has purchase order to confirm payment from buyer"),
    )

    # pylint: disable=no-member
    def __str__(self):
        return f"{self.batch_order.owner}'s quote for course {self.batch_order.relation.course}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def unsigned(self):
        """
        Returns boolean value whether the quote is not yet signed by both parties (organization
        and buyer)
        """
        return self.organization_signed_on is None and self.buyer_signed_on is None

    @property
    def is_signed_by_organization(self):
        """
        Returns boolean value whether the quote is signed by the organization
        """
        return self.organization_signed_on is not None and self.buyer_signed_on is None

    @property
    def is_fully_signed(self):
        """
        Returns boolean value whether the quote has been signed by both parties (organization
        and buyer)
        """
        return (
            self.organization_signed_on is not None and self.buyer_signed_on is not None
        )

    @property
    def has_received_purchase_order(self):
        """
        Returns boolean value whether the quote has been fully signed and purchase order
        has been received
        """
        return self.is_fully_signed and self.has_purchase_order_received
