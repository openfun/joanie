"""
Declare and configure the models for Joanie's events
"""
import logging

from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from joanie.core import enums
from joanie.core.models.base import BaseModel

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """
    Event represents a message to a user
    """

    user = models.ForeignKey(
        to="core.User",
        verbose_name=_("user"),
        related_name="events",
        on_delete=models.CASCADE,
    )
    level = models.CharField(
        _("level"),
        max_length=20,
        choices=enums.EVENT_LEVEL_CHOICES,
        default=enums.EVENT_INFO,
    )
    read = models.BooleanField(_("read"), default=False)

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")

    def __str__(self):
        return f"{self.user}: {self.level} {self.type}"

    def get_abilities(self, user):
        """
        The user has all the abilities on their own events.
        """
        is_owner = user == self.user
        return {"delete": is_owner}
