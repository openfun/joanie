"""
Declare and configure the models for Joanie's contracts
"""
import logging
import textwrap

from django.conf import settings
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

import markdown

from joanie.core import enums
from joanie.core.utils import image_to_base64
from joanie.core.utils.issuers import generate_document

from .base import BaseModel
from .products import Order

logger = logging.getLogger(__name__)


class ContractDefinition(BaseModel):
    """
    Contract definition describes template and markdown to generate user contracts
    """

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
        choices=enums.CONTRACT_NAME_CHOICES,
        default=enums.CONTRACT_DEFINITION,
    )

    class Meta:
        db_table = "joanie_contract_definition"
        verbose_name = _("Contract definition")
        verbose_name_plural = _("Contract definitions")

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

    def get_document_context(self, order):
        """
        Build the contract document context for the given language.
        """
        organization = order.organization
        owner = order.owner
        product = order.product

        return {
            "contract": {
                "body": self.get_body_in_html(),
                "title": self.title,
            },
            "course": {
                "name": product.safe_translation_getter(
                    "title", language_code=self.language
                ),
            },
            "student": {
                "name": owner.get_full_name() or owner.username,
                "address": owner.addresses.filter(is_main=True).first(),
            },
            "organization": {
                "logo": image_to_base64(organization.logo),
                "name": organization.safe_translation_getter(
                    "title", language_code=self.language
                ),
                "signature": image_to_base64(organization.signature),
            },
        }

    def generate_document(self, order):
        """
        Generate the contract definition.
        """
        context = self.get_document_context(order)
        file_bytes = generate_document(
            name=order.product.contract_definition.name, context=context
        )
        return context, file_bytes


class Contract(BaseModel):
    """
    Contract represents and records the user contract issued as part of an order.
    """

    definition = models.ForeignKey(
        to=ContractDefinition,
        verbose_name=_("Contract definition"),
        related_name="contracts",
        on_delete=models.RESTRICT,
        editable=False,
    )
    order = models.OneToOneField(
        Order,
        verbose_name=_("order"),
        on_delete=models.PROTECT,
        editable=False,
    )

    # Set on contract generation
    definition_checksum = models.CharField(
        max_length=255, editable=False, blank=True, null=True
    )
    context = models.JSONField(
        _("context"),
        blank=True,
        help_text=_("Localized data snapshot on contract signature"),
        editable=False,
        null=True,
    )
    signature_backend_reference = models.CharField(
        blank=True,
        editable=False,
        max_length=255,
        null=True,
        verbose_name=_("Reference in the external signature backend"),
    )

    # Set on student signature
    signed_on = models.DateTimeField(
        _("Date and time of issuance"), null=True, blank=True, editable=False
    )
    # Set when contract is sent to signature provider
    submitted_for_signature_on = models.DateTimeField(
        _("Date and time we send the contract to signature provider"),
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        db_table = "joanie_contract"
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")
        ordering = ["-created_on"]
        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        models.Q(definition_checksum__isnull=True)
                        & models.Q(context=None)
                    )
                    | (
                        ~models.Q(definition_checksum="")
                        & ~models.Q(definition_checksum__isnull=True)
                        & ~models.Q(context=None)
                        & ~models.Q(context={})
                    )
                ),
                name="generate_complete",
                violation_error_message=(
                    "Make sure to complete all fields when generating a contract."
                ),
            ),
            models.CheckConstraint(
                check=(
                    (
                        models.Q(signed_on__isnull=False)
                        & ~models.Q(definition_checksum="")
                        & ~models.Q(definition_checksum__isnull=True)
                        & ~models.Q(context=None)
                        & ~models.Q(context={})
                    )
                    | (models.Q(signed_on__isnull=True))
                ),
                name="signed_on_complete",
                violation_error_message=(
                    "Make sure to complete all fields before signing contract."
                ),
            ),
            models.CheckConstraint(
                check=~models.Q(
                    signed_on__isnull=False, submitted_for_signature_on__isnull=False
                ),
                name="reference_datetime_not_both_set",
                violation_error_message=(
                    "Make sure to not have both datetime fields set simultaneously."
                ),
            ),
            models.CheckConstraint(
                check=(
                    (
                        models.Q(signed_on__isnull=False)
                        | models.Q(submitted_for_signature_on__isnull=False)
                    )
                    | models.Q(signature_backend_reference__isnull=True)
                ),
                name="signature_backend_reference_must_have_date",
                violation_error_message=(
                    "Make sure to have a date attached to the signature backend reference."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.order.owner}'s contract for course {self.order.course}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)
