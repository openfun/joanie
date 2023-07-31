"""
Declare and configure the models for the certifications part
"""
import logging

from django.conf import settings
from django.db import models
from django.utils.module_loading import import_string
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models
from parler.utils import get_language_settings

from joanie.core.utils import image_to_base64, merge_dict

from .base import BaseModel

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
    
    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """

        # TODO : Who can delete a CertificateDefinition?
        return {
            "delete": True,
            "get": True,
            "patch": True,
            "put": True,
            "set_role_to": True,
        }


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
        verbose_name=_("order"),
        on_delete=models.PROTECT,
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

    def __str__(self):
        return f"{self.order.owner}'s certificate for course {self.order.course}"

    @property
    def document(self):
        """
        Get the document related to the certificate instance.
        """
        document_issuer = import_string(self.certificate_definition.template)
        try:
            context = self.get_document_context()
        except ValueError as exception:
            logger.error(
                "Cannot get document context to generate certificate.",
                exc_info=exception,
            )
            return None

        document = document_issuer(identifier=self.id, context_query=context)
        return document.create(persist=False)

    def _set_localized_context(self):
        """
        Update or create the certificate context for all languages.

        Saving is left to the caller.
        """
        context = {}
        related_product = self.order.product
        organization = self.order.organization

        for language, __ in settings.LANGUAGES:
            context[language] = {
                "course": {
                    "name": related_product.safe_translation_getter(
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
        organization = self.order.organization
        owner = self.order.owner

        base_context = {
            "creation_date": self.issued_on.isoformat(),
            "student": {
                "name": owner.get_full_name() or owner.username,
            },
            "organization": {
                "representative": organization.representative,
                "signature": image_to_base64(organization.signature),
                "logo": image_to_base64(organization.logo),
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

        models.Model.save(self, *args, **kwargs)
