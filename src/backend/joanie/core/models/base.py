"""
Base model for the apps of the Joanie project.

In this base model, we activate generic behaviours that apply to all our models and enforce
checks and validation that go further than what Django is doing.
"""

import uuid
from itertools import chain

from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from joanie.core.utils import file_checksum


class BaseModel(models.Model):
    """Base model for all the models of the apps"""

    id = models.UUIDField(
        verbose_name=_("id"),
        help_text=_("primary key for the record as UUID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_on = models.DateTimeField(
        verbose_name=_("created on"),
        help_text=_("date and time at which a record was created"),
        auto_now_add=True,
        editable=False,
    )
    updated_on = models.DateTimeField(
        verbose_name=_("updated on"),
        help_text=_("date and time at which a record was last updated"),
        auto_now=True,
        editable=False,
    )

    class Meta:
        """Options for the ``BaseTranslatableModel`` model."""

        abstract = True
        ordering = ["created_on"]

    def __repr__(self, dict_repr=False):
        return str(self.to_dict())

    def get_cache_key(self, prefix, is_language_sensitive=False, language=None):
        """
        Return a cache key for the instance. If the key is going to be used for multilingual
        content, an extra argument `is_local_sensitive` can be set to True to bind
        the active language to the cache key. Alternatively, a `language` argument is
        also accepted to bind a specific language to the cache key.
        """
        cache_key = f"{prefix:s}-{self.id!s}-{self.updated_on.timestamp():.6f}"
        if is_language_sensitive or language:
            current_language = language or get_language()
            cache_key = f"{cache_key}-{current_language}"

        return cache_key

    def to_dict(self):
        """Return a dictionary representation of the model."""
        opts = self._meta
        data = {}
        for field in chain(opts.concrete_fields, opts.private_fields):
            data[field.name] = field.value_from_object(self)
        for field in opts.many_to_many:
            data[field.name] = [related.id for related in field.value_from_object(self)]
        return data


class DocumentImage(BaseModel):
    """
    DocumentImage represents an image used in a document.
    """

    checksum = models.CharField(
        _("checksum"),
        max_length=64,
        help_text=_("SHA-256 Checksum of the file"),
        editable=False,
        unique=True,
    )
    file = models.ImageField(
        _("file"),
        max_length=255,
        help_text=_("File used in the certificate"),
        editable=False,
        null=False,
    )

    def __str__(self):
        return self.file.name

    def save(self, *args, **kwargs):
        """
        Save the instance and calculate the checksum if it is not set.
        """

        if not self.checksum:
            self.checksum = file_checksum(self.file)

        super().save(*args, **kwargs)
