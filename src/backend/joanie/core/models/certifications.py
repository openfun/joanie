"""
Declare and configure the models for the certifications part
"""

import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language, override
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models
from parler.utils import get_language_settings

from joanie.core import enums
from joanie.core.models.base import BaseModel, DocumentImage
from joanie.core.utils import file_checksum, image_to_base64, merge_dict

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
    template = models.CharField(
        _("template to generate pdf"),
        choices=enums.CERTIFICATE_NAME_CHOICES,
        max_length=255,
        db_index=True,
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
    images = models.ManyToManyField(
        to=DocumentImage,
        verbose_name=_("images"),
        related_name="certificates",
        editable=False,
        blank=True,
    )
    localized_context = models.JSONField(
        _("context"),
        help_text=_("Localized data that needs to be frozen on certificate creation"),
        editable=False,
        encoder=DjangoJSONEncoder,
    )

    class Meta:
        db_table = "joanie_certificate"
        verbose_name = _("Certificate")
        verbose_name_plural = _("Certificates")
        ordering = ["-issued_on"]
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
        """Returns the certificate course depending from the related order or enrollment."""
        if self.order:
            course = (
                self.order.course
                if self.order.course
                else self.order.enrollment.course_run.course
            )
        else:
            course = self.enrollment.course_run.course

        return course

    @property
    def owner(self):
        """Returns the certificate owner depending from the related order or enrollment."""
        return self.order.owner if self.order else self.enrollment.user

    def _set_localized_context(self, created=True):
        """
        Update or create the certificate context for all languages.

        Saving is left to the caller.
        """
        context = {}
        title_object = (
            self.order.product if self.order else self.enrollment.course_run.course
        )
        new_images = set()
        for language, __ in settings.LANGUAGES:
            context[language] = {
                "course": {
                    "name": title_object.safe_translation_getter(
                        "title", language_code=language
                    ),
                },
                "organizations": [],
            }

            for organization in self.course.organizations.all():
                logo_id = None
                signature_id = None
                if organization.signature:
                    signature_checksum = file_checksum(organization.signature)
                    (signature, _created) = DocumentImage.objects.get_or_create(
                        checksum=signature_checksum,
                        defaults={"file": organization.signature},
                    )
                    new_images.add(signature)
                    signature_id = str(signature.id)

                if organization.logo:
                    logo_checksum = file_checksum(organization.logo)
                    (logo, _created) = DocumentImage.objects.get_or_create(
                        checksum=logo_checksum,
                        defaults={"file": organization.logo},
                    )
                    new_images.add(logo)
                    logo_id = str(logo.id)

                context[language]["organizations"].append(
                    {
                        "name": organization.safe_translation_getter(
                            "title", language_code=language
                        ),
                        "representative": organization.signatory_representative
                        or organization.representative,
                        "representative_profession": organization.signatory_representative_profession
                        if organization.signatory_representative
                        else organization.representative_profession,
                        "signature_id": signature_id,
                        "logo_id": logo_id,
                    }
                )

        self.localized_context = context

        if created is False:
            return new_images
        else:
            self.images.set(new_images)

    @property
    def verification_uri(self):
        """
        Return the verification uri for the certificate if
        this one is a degree certificate.
        """
        if self.certificate_definition.template != enums.DEGREE:
            return None

        # - Retrieve the current language code or a fallback if the language is not available
        current_language_code = get_language_settings(get_language()).get("code")
        site = Site.objects.get_current()
        with override(current_language_code, True):
            path = reverse(
                "certificate-verification", kwargs={"certificate_id": self.pk}
            )

        return f"https://{site.domain}{path}"

    def get_document_context(self, language_code=None):
        """
        Build the certificate document context for the given language.
        If no language_code is provided, we use the active language.
        """
        language_settings = get_language_settings(language_code or get_language())

        base_context = {
            "id": str(self.pk),
            "creation_date": self.issued_on,
            "delivery_stamp": timezone.now(),
            "verification_link": self.verification_uri,
            "student": {
                "name": self.owner.name,
            },
            "site": {
                "name": settings.JOANIE_CATALOG_NAME,
                "hostname": settings.JOANIE_CATALOG_BASE_URL,
            },
        }

        try:
            localized_context = self.localized_context[language_settings["code"]]
        except KeyError:
            # - Otherwise use the first entry of the localized context
            localized_context = list(self.localized_context.values())[0]

        # - Inject the assets
        for index, organization in enumerate(localized_context["organizations"]):
            signature_id = organization.get("signature_id")
            logo_id = organization.get("logo_id")
            signature_file = None
            logo_file = None

            if signature_id:
                if signature := self.images.filter(pk=signature_id).first():
                    signature_file = image_to_base64(signature.file)

            if logo_id:
                if logo := self.images.filter(pk=logo_id).first():
                    logo_file = image_to_base64(logo.file)
            else:
                logger.error(
                    "Organization %s does not have a logo.", self.organization.id
                )

            organization["signature"] = signature_file
            organization["logo"] = logo_file

            localized_context["organizations"][index] = organization

        return merge_dict(base_context, localized_context)

    def save(self, *args, **kwargs):
        """On creation, create a context for each active languages"""

        self.full_clean()

        is_new = self.created_on is None
        new_images = None

        if is_new:
            new_images = self._set_localized_context(created=False)

        super().save(*args, **kwargs)

        if new_images:
            self.images.set(new_images)
