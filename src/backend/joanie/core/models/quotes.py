"""
Declare and configure the models for Joanie's quotes
"""

import textwrap

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils import timezone
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
    # Only the organization confirms the signature of the document
    organization_signed_on = models.DateTimeField(
        _("Date and time organization signed on"), null=True, blank=True, editable=False
    )
    has_purchase_order = models.BooleanField(
        verbose_name=_("purchase order to confirm payment"),
        editable=False,
        default=False,
        help_text=_("Quote has purchase order to confirm payment from buyer"),
    )
    reference = models.CharField(
        _("reference"),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Incremental quote reference number, e.g. FUN_2025_0000001"),
    )

    class Meta:
        db_table = "joanie_quote"
        verbose_name = _("Quote")
        verbose_name_plural = _("Quotes")
        ordering = ["-created_on"]
        constraints = [
            models.CheckConstraint(
                check=~(
                    models.Q(organization_signed_on__isnull=True)
                    & models.Q(has_purchase_order=True)
                ),
                name="organization_must_sign_quote_before_receiving_purchase_order",
                violation_error_message=(
                    "Organization must sign quote before receiving purchase order."
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

    def clean(self):
        """
        When the object is created, add a unique reference to it
        """
        if not self.reference:
            year = timezone.now().year
            prefix_reference = f"{settings.JOANIE_PREFIX_QUOTE_REFERENCE}_{year}_"
            with transaction.atomic():
                # select_for_update() will lock row the queryset until the end of the transaction
                last = (
                    Quote.objects.filter(reference__startswith=prefix_reference)
                    .order_by("-reference")
                    .select_for_update()
                    .first()
                )
                next_number = 0
                if last and last.reference:
                    last_number = int(last.reference.split("_")[-1])
                    next_number = last_number + 1

                reference = f"{prefix_reference}{next_number:07d}"

                while self.__class__.objects.filter(reference=reference).exists():
                    # This while loop handles cases when concurrent requests are made,
                    # ensuring the reference is unique.
                    next_number += 1
                    reference = f"{prefix_reference}{next_number:07d}"

                self.reference = reference

        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def tag_organization_signed_on(self):
        """Updates the quote with the datetime of signature from the organization"""
        self.organization_signed_on = timezone.now()
        self.save()

    def tag_has_purchase_order(self):
        """Updates the quote with the reception of the purchase order"""
        self.has_purchase_order = True
        self.save()

    @property
    def is_signed_by_organization(self):
        """
        Returns boolean value whether the quote is signed by the organization only.
        """
        return self.organization_signed_on is not None

    @property
    def has_received_purchase_order(self):
        """
        Returns boolean value whether the quote has been fully signed and purchase order
        has been received
        """
        return self.is_signed_by_organization and self.has_purchase_order

    def get_abilities(self, user):
        """
        Compute and return abilities for the user taking into account their
        roles on other objects.
        """

        download_quote = False
        confirm_quote = False
        confirm_bank_transfer = False

        if user.is_authenticated:
            abilities = self.batch_order.organization.get_abilities(user=user)
            download_quote = abilities.get("download_quote", False)
            confirm_quote = abilities.get("confirm_quote", False)
            confirm_bank_transfer = abilities.get("confirm_bank_transfer", False)

        return {
            "download_quote": download_quote,
            "confirm_quote": confirm_quote,
            "confirm_bank_transfer": confirm_bank_transfer,
        }
