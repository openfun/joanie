"""
Declare and configure the models for Joanie's notifications
"""
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from joanie.core import enums
from joanie.core.models.base import BaseModel

logger = logging.getLogger(__name__)


class Notification(BaseModel):
    """
    Notification represents a message to a user
    """

    user = models.ForeignKey(
        to="core.User",
        verbose_name=_("user"),
        related_name="notifications",
        on_delete=models.CASCADE,
    )
    message = models.TextField(_("message"))
    level = models.CharField(
        _("level"),
        max_length=20,
        choices=enums.NOTIFICATION_LEVEL_CHOICES,
        default=enums.NOTIFICATION_INFO,
    )
    read = models.BooleanField(_("read"), default=False)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")

    def __str__(self):
        return f"{self.user}: {self.message}"

    def get_abilities(self, user):
        """
        The user has all the abilities on their own notifications.
        """
        is_owner = user == self.user
        return {"delete": is_owner}
