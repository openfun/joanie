"""
Declare and configure the models for Joanie's contracts
"""
import logging
import textwrap
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

import markdown

from joanie.core import enums
from joanie.core.models.base import BaseModel
from joanie.core.utils import contract_definition, issuers

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

    def generate_document(self, order):
        """
        Generate the contract definition.
        """
        context = contract_definition.generate_document_context(
            contract_definition=self, user=order.owner, order=order
        )
        file_bytes = issuers.generate_document(
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
        "core.order",
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

    # Set when contract is sent to signature provider
    submitted_for_signature_on = models.DateTimeField(
        _("Date and time we send the contract to signature provider"),
        null=True,
        blank=True,
        editable=False,
    )

    # Set on student signature
    student_signed_on = models.DateTimeField(
        _("Date and time of issuance"), null=True, blank=True, editable=False
    )

    # Set on organization signature
    organization_signatory = models.ForeignKey(
        to="core.user",
        verbose_name=_("organization signatory"),
        related_name="signed_contracts",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        editable=False,
    )
    organization_signed_on = models.DateTimeField(
        _("Date and time the organization signed the contract"),
        blank=True,
        null=True,
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
                        models.Q(student_signed_on__isnull=False)
                        & ~models.Q(definition_checksum="")
                        & ~models.Q(definition_checksum__isnull=True)
                        & ~models.Q(context=None)
                        & ~models.Q(context={})
                    )
                    | (models.Q(student_signed_on__isnull=True))
                ),
                name="student_signed_on_complete",
                violation_error_message=(
                    "Make sure to complete all fields before signing contract."
                ),
            ),
            models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        student_signed_on__isnull=True,
                        organization_signed_on__isnull=True,
                    )
                    | models.Q(
                        submitted_for_signature_on__isnull=False,
                        student_signed_on__isnull=False,
                        organization_signed_on__isnull=True,
                    )
                    | models.Q(
                        submitted_for_signature_on__isnull=True,
                        student_signed_on__isnull=False,
                        organization_signed_on__isnull=False,
                    )
                ),
                name="incoherent_signature_dates",
                violation_error_message="Signature dates are incoherent.",
            ),
            models.CheckConstraint(
                check=(
                    (
                        models.Q(student_signed_on__isnull=False)
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

    # pylint: disable=no-member
    def __str__(self):
        course = self.order.course if self.order.course else self.order.enrollment
        return f"{self.order.owner}'s contract for course {course}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def tag_submission_for_signature(self, reference, checksum, context):
        """
        Updates the contract from an order that we have submitted to the signature provider.
        """
        self.submitted_for_signature_on = timezone.now()
        self.context = context
        self.definition_checksum = checksum
        self.signature_backend_reference = reference
        self.save()

    def reset_submission_for_signature(self):
        """
        Contract that was submitted to a signature procedure should be reset when it is refused
        by the signer.
        """
        self.submitted_for_signature_on = None
        self.context = None
        self.definition_checksum = None
        self.signature_backend_reference = None
        self.save()

    def is_eligible_for_signing(self):
        """
        Determine if a contract is still eligible for signing, call this method on
        the contract instance. If it has not been submitted to signature, we
        make sure to return False.
        """
        if not self.submitted_for_signature_on:
            return False

        return timezone.now() < self.submitted_for_signature_on + timedelta(
            seconds=settings.JOANIE_SIGNATURE_VALIDITY_PERIOD
        )

    def get_abilities(self, user):
        """
        Compute and return abilities for the user taking into account their
        roles on other objects.
        """

        can_sign = False

        if user.is_authenticated:
            abilities = self.order.organization.get_abilities(user=user)
            can_sign = abilities.get("sign_contracts", False)

        return {
            "sign": can_sign,
        }
