"""Site extension models for the Joanie project."""
import textwrap

from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _

import markdown
from parler import models as parler_models

from joanie.core.models.base import BaseModel


class SiteConfig(parler_models.TranslatableModel, BaseModel):
    """Model to extend the django site model."""

    site = models.OneToOneField(
        to=Site,
        related_name="site_config",
        verbose_name=_("site"),
        on_delete=models.CASCADE,
    )

    translations = parler_models.TranslatedFields(
        terms_and_conditions=models.TextField(
            verbose_name=_("terms and conditions"),
            help_text=_("Terms and conditions for the site in Markdown format."),
            blank=True,
        ),
    )

    class Meta:
        db_table = "joanie_site_config"
        verbose_name = _("Site config")
        verbose_name_plural = _("Site configs")

    def __str__(self):
        return f"Site config for {self.site.name}"

    def get_terms_and_conditions_in_html(self, language=None):
        """Return the terms and conditions in html format."""
        content = self.safe_translation_getter(
            "terms_and_conditions",
            language_code=language,
            any_language=True,
            default="",
        )

        return markdown.markdown(textwrap.dedent(content))
