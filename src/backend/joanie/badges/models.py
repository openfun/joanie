"""
Declare and configure the models for the badges part
"""
from functools import lru_cache

from django.db import models
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models

from joanie.core.models import BaseModel, User


@lru_cache
def get_badge_provider_choices():
    """Get BadgeProvider choices. Should be evaluated once."""
    # pylint: disable=fixme

    # FIXME
    # Dynamically list available providers
    choices = ("FAK", "OBF")
    return models.TextChoices("BadgeProvider", choices)


class Badge(parler_models.TranslatableModel, BaseModel):
    """
    Issuable badges for a provider.
    """

    translations = parler_models.TranslatedFields(
        name=models.CharField(
            verbose_name=_("Name"),
            help_text=_(
                "Should be filled with the badge name from configured provider"
            ),
            max_length=100,
            editable=False,
        ),
        description=models.TextField(
            _("Description"),
            help_text=_(
                "Should be filled with the badge description from configured provider"
            ),
            editable=False,
        ),
    )

    provider = models.CharField(
        _("Provider"),
        help_text=_(
            "Should be filled with configured provider name/code for this badge"
        ),
        max_length=3,
        choices=get_badge_provider_choices().choices,
        db_index=True,
        editable=False,
    )

    iri = models.URLField(
        _("IRI"),
        help_text=_(
            "Generated badge IRI, usually the URL pointing to the badge created for a provider"
        ),
        editable=False,
        db_index=True,
        unique=True,
    )

    class Meta:
        """Options for the Badge model"""

        db_table = "joanie_badge"
        ordering = ["created_on"]
        verbose_name = _("Badge")
        verbose_name_plural = _("Badges")

    def __str__(self):
        return f"{self.provider}: {self.safe_translation_getter('name')}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)


class IssuedBadge(BaseModel):
    """
    Issued badges for a resource.
    """

    iri = models.URLField(
        _("Issued badge IRI"),
        help_text=_("Issued badge IRI, usually the URL pointing to issued badge"),
        editable=False,
    )

    resource_link = models.URLField(
        _("Resource link"),
        help_text=_(
            "Link to the resource the badge has been issued for (e.g. a course session)"
        ),
        editable=False,
        blank=True,
    )

    user = models.ForeignKey(
        to=User,
        verbose_name=_("User"),
        related_name="issued_badges",
        on_delete=models.CASCADE,
        editable=False,
    )

    badge = models.ForeignKey(
        to=Badge,
        verbose_name=_("Badge"),
        related_name="issued",
        on_delete=models.RESTRICT,
        editable=False,
    )

    assertion = models.JSONField(
        _("Issued badge assertion"),
        help_text=_("A JSON object allowing to verify an issued badge"),
        editable=False,
        blank=True,
        null=True,
    )

    class Meta:
        """Options for the Issued Badge model"""

        db_table = "joanie_issued_badge"
        ordering = ["created_on"]
        verbose_name = _("Issued badge")
        verbose_name_plural = _("Issued badges")

    def __str__(self):
        return f"{self.badge} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)
