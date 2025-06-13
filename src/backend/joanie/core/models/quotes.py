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
from parler import models as parler_models

from joanie.core import enums
from joanie.core.models.base import BaseModel, DocumentImage


class QuoteDefinition(parler_models.TranslatableModel, BaseModel):
    """
    Quote definition describes the template and markdown to generate quotes.
    """

    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255, blank=True),
        description=models.TextField(_("description"), max_length=500, blank=True),
    )
    body = models.TextField(_("body"), blank=True)
    language = models.CharField(
        max_length=10,
        choices=lazy(lambda: settings.LANGUAGES, tuple)(),
        verbose_name=_("language"),
        help_text=_("Language of the quote definition"),
    )
    name = models.CharField(
        _("template name to generate pdf"),
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

    class Meta:
        db_table = "joanie_quote_definition"
        verbose_name = _("Quote definition")
        verbose_name_plural = _("Quote definitions")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True)

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
    # Once the quote is signed by both parties, the buyer should send a purchase
    # order to confirm his engagement. The confirmation will done manually too.
    has_purchase_order = models.BooleanField(
        verbose_name=_("purchase order to confirm payment"),
        editable=False,
        default=False,
        help_text=_("Quote has purchase order to confirm payment from buyer"),
    )

    class Meta:
        db_table = "joanie_quote"
        verbose_name = _("Quote")
        verbose_name_plural = _("Quotes")
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
                    models.Q(has_purchase_order=True)
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

    # pylint: disable=no-member
    def __str__(self):
        return f"Quote for course {self.batch_order.relation.course.code}"

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
        Returns boolean value whether the quote is signed by the organization only.
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
        return self.is_fully_signed and self.has_purchase_order
