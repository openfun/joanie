from django.db import models

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models

from . import products as products_models


class CertificateDefinition(parler_models.TranslatableModel):
    """
    Certificate definition
    """
    # code??
    name = models.SlugField(verbose_name=_("name"), max_length=255, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(verbose_name=_("title"), max_length=255),
        description=models.TextField(verbose_name=_("description"), max_length=500, blank=True),
    )
    # howard template used to generate pdf certificate??
    template = models.CharField(
        verbose_name=_("template to generate pdf"), max_length=255, blank=True, null=True,
    )

    class Meta:
        db_table = "joanie_certificate_definition"
        verbose_name = _("Certificate definition")
        verbose_name_plural = _("Certificate definitions")

    def __str__(self):
        return self.title


class Certificate(models.Model):
    certificate_definition = models.ForeignKey(
        CertificateDefinition,
        related_name='certificates_issued',
        on_delete=models.RESTRICT,
    )
    order = models.ForeignKey(products_models.Order, on_delete=models.PROTECT)
    attachment = models.FileField()  # ? pdf generated with marion
    issued_on = models.DateTimeField(_("issued on date"), default=timezone.now)

    class Meta:
        db_table = "joanie_certificate"
        verbose_name = _("Certificate")
        verbose_name_plural = _("Certificates")

    def __str__(self):
        return f"Certificate: {self.certificate_definition} for {self.order.owner}"
