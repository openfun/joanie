"""
Declare and configure the models for the certifications part
"""
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models
from parler.utils import get_language_settings

from joanie.core import enums
from joanie.core.models.base import BaseModel
from joanie.core.utils import image_to_base64, merge_dict
from joanie.core.utils.issuers import generate_document

logger = logging.getLogger(__name__)


class CertificateDefinition(parler_models.TranslatableModel, BaseModel):
    """
    Certificate definition describes templates used to generate user certificates
    """

    name = models.CharField(_("name"), max_length=255, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255),
        description=models.TextField(_("description"), max_length=500, blank=True),
    )
    # howard template used to generate pdf certificate
    template = models.CharField(
        _("template to generate pdf"),
        choices=enums.CERTIFICATE_NAME_CHOICES,
        max_length=255,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "joanie_certificate_definition"
        verbose_name = _("Certificate definition")
        verbose_name_plural = _("Certificate definitions")
        ordering = ["-created_on"]

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True)

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


class Certificate(BaseModel):
    """
    Certificate represents and records all user certificates issued as part of an order
    """

    issued_on = models.DateTimeField(
        _("Date of issuance"), auto_now=True, editable=False
    )

    certificate_definition = models.ForeignKey(
        to=CertificateDefinition,
        verbose_name=_("Certificate definition"),
        related_name="certificates",
        on_delete=models.RESTRICT,
        editable=False,
    )

    order = models.OneToOneField(
        # disable=all is necessary to avoid an AstroidImportError because of our models structure
        # Astroid is looking for a module models.py that does not exist
        "core.Order",  # pylint: disable=all
        blank=True,
        null=True,
        verbose_name=_("order"),
        on_delete=models.PROTECT,
        editable=False,
    )
    enrollment = models.OneToOneField(
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        to="core.enrollment",
        verbose_name=_("enrollment"),
        editable=False,
    )
    organization = models.ForeignKey(
        on_delete=models.PROTECT,
        to="core.organization",
        verbose_name=_("organization"),
        editable=False,
    )

    localized_context = models.JSONField(
        _("context"),
        help_text=_("Localized data that needs to be frozen on certificate creation"),
        editable=False,
    )

    class Meta:
        db_table = "joanie_certificate"
        verbose_name = _("Certificate")
        verbose_name_plural = _("Certificates")
        ordering = ["-created_on"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(("order__isnull", False), ("enrollment__isnull", True))
                    | models.Q(("order__isnull", True), ("enrollment__isnull", False))
                ),
                name="either_order_or_enrollment",
                violation_error_message="Certificate should have either an order or an enrollment",
            )
        ]

    def __str__(self):
        return f"{self.owner}'s certificate for course {self.course}"

    @property
    def course(self):
        """Returns the certificate owner depending from the related order or enrollment."""
        return self.order.course if self.order else self.enrollment.course_run.course

    @property
    def owner(self):
        """Returns the certificate owner depending from the related order or enrollment."""
        return self.order.owner if self.order else self.enrollment.user

    def generate_document(self):
        """
        Generate the certificate document through the certificate definition template
        and the document context.
        """

        try:
            context = self.get_document_context()
        except ValueError as exception:
            logger.error(
                "Cannot get document context to generate certificate.",
                exc_info=exception,
            )
            return None, None

        file_bytes = generate_document(
            name=self.certificate_definition.template, context=context
        )
        return file_bytes, context

    def _set_localized_context(self):
        """
        Update or create the certificate context for all languages.

        Saving is left to the caller.
        """
        context = {}
        organization = self.organization
        title_object = (
            self.order.product if self.order else self.enrollment.course_run.course
        )

        for language, __ in settings.LANGUAGES:
            context[language] = {
                "course": {
                    "name": title_object.safe_translation_getter(
                        "title", language_code=language
                    ),
                },
                "organization": {
                    "name": organization.safe_translation_getter(
                        "title", language_code=language
                    ),
                },
            }
        self.localized_context = context

    def get_document_context(self, language_code=None):
        """
        Build the certificate document context for the given language.
        If no language_code is provided, we use the active language.
        """

        language_settings = get_language_settings(language_code or get_language())
        site = Site.objects.get_current()

        base_context = {
            "id": str(self.pk),
            "creation_date": self.issued_on,
            "delivery_stamp": timezone.now(),
            "student": {
                "name": self.owner.get_full_name() or self.owner.username,
            },
            "organization": {
                "representative": self.organization.representative,
                "signature": image_to_base64(self.organization.signature),
                "logo": image_to_base64(self.organization.logo),
            },
            "site": {
                "name": site.name,
                "hostname": "https://" + site.domain,
            },
        }

        try:
            localized_context = self.localized_context[language_settings["code"]]
        except KeyError:
            # - Otherwise use the first entry of the localized context
            localized_context = list(self.localized_context.values())[0]

        return merge_dict(base_context, localized_context)

    def save(self, *args, **kwargs):
        """On creation, create a context for each active languages"""

        self.full_clean()

        is_new = self.created_on is None
        if is_new:
            self._set_localized_context()

        super().save(*args, **kwargs)
