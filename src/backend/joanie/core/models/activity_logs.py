"""
Declare and configure the models for Joanie's activity logs.
"""

import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from joanie.core import enums
from joanie.core.models.base import BaseModel

logger = logging.getLogger(__name__)


class ActivityLogContextField(models.JSONField):
    """
    ActivityLogContextField is a JSONField with validators for each type of ActivityLog
    """

    def validate(self, value, model_instance):
        """
        Validate the context field
        """
        if not isinstance(value, dict):
            raise ValidationError("The context field must be a dictionary")

        activity_log_type = model_instance.type
        if activity_log_type == enums.ACTIVITY_LOG_TYPE_NOTIFICATION:
            self.validate_notification(value)
        elif activity_log_type in [
            enums.ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
            enums.ACTIVITY_LOG_TYPE_PAYMENT_FAILED,
        ]:
            self.validate_payment_type(value)
        else:
            raise ValidationError(f"Unknown activity log type: {activity_log_type}")

    def validate_notification(self, value):
        """
        Validate the context field for an activity log
        """
        if value:
            raise ValidationError("The context field must be an empty dictionary")

    def validate_payment_type(self, value):
        """
        Validate the context field for a payment type activity log
        """
        if "order_id" not in value:
            raise ValidationError("The context field must have an order_id")


class ActivityLog(BaseModel):
    """
    Activity log represents an event that happened in the system
    """

    user = models.ForeignKey(
        to="core.User",
        verbose_name=_("user"),
        related_name="activity_logs",
        on_delete=models.CASCADE,
    )
    level = models.CharField(
        _("level"),
        max_length=20,
        choices=enums.ACTIVITY_LOG_LEVEL_CHOICES,
        default=enums.ACTIVITY_LOG_LEVEL_INFO,
    )
    context = ActivityLogContextField(
        _("context"),
        default=dict,
    )
    type = models.CharField(
        _("type"),
        max_length=20,
        choices=lazy(lambda: enums.ACTIVITY_LOG_TYPE_CHOICES, tuple)(),
        default=enums.ACTIVITY_LOG_TYPE_NOTIFICATION,
    )

    class Meta:
        verbose_name = _("activity_log")
        verbose_name_plural = _("activity_logs")

    @classmethod
    def create_payment_succeeded_activity_log(cls, order):
        """
        Create a payment succeeded activity log
        """
        return cls.objects.create(
            user=order.owner,
            level=enums.ACTIVITY_LOG_LEVEL_SUCCESS,
            context={"order_id": str(order.id)},
            type=enums.ACTIVITY_LOG_TYPE_PAYMENT_SUCCEEDED,
        )

    @classmethod
    def create_payment_failed_activity_log(cls, order):
        """
        Create a payment failed activity log
        """
        return cls.objects.create(
            user=order.owner,
            level=enums.ACTIVITY_LOG_LEVEL_ERROR,
            context={"order_id": str(order.id)},
            type=enums.ACTIVITY_LOG_TYPE_PAYMENT_FAILED,
        )

    def __str__(self):
        return f"{self.user}: {self.level} {self.type}"

    def save(self, *args, **kwargs):
        """
        Validate the context field
        """
        self.full_clean()
        super().save(*args, **kwargs)
