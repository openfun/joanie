"""
Declare and configure the models for the certifications part
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models

from . import products as products_models


class CertificateDefinition(parler_models.TranslatableModel):
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

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True)


class Certificate(models.Model):
    """
    Certificate represents and records all user certificates issued as part of an order
    """

    certificate_definition = models.ForeignKey(
        CertificateDefinition,
        verbose_name=_("certificate definition"),
        related_name="certificates_issued",
        on_delete=models.RESTRICT,
    )
    order = models.OneToOneField(
        products_models.Order,
        verbose_name=_("order"),
        on_delete=models.PROTECT,
    )
    # attachment pdf will be generated with marion from certificate definition
    attachment = models.FileField(_("attachment"))
    issued_on = models.DateTimeField(_("issued on date"), default=timezone.now)

    class Meta:
        db_table = "joanie_certificate"
        verbose_name = _("Certificate")
        verbose_name_plural = _("Certificates")

    def __str__(self):
        return f"{self.certificate_definition} for {self.order.owner}"
