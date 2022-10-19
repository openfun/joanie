"""
Base model for the apps of the Joanie project.

In this base model, we activate generic behaviours that apply to all our models and enforce
checks and validation that go further than what Django is doing.
"""
import uuid
from itertools import chain

from django.db import models
from django.utils.translation import gettext_lazy as _


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

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __repr__(self, dict_repr=False):
        return str(self.to_dict())

    def to_dict(self):
        """Return a dictionary representation of the model."""
        opts = self._meta
        data = {}
        for field in chain(opts.concrete_fields, opts.private_fields):
            data[field.name] = field.value_from_object(self)
        for field in opts.many_to_many:
            data[field.name] = [related.id for related in field.value_from_object(self)]
        return data
