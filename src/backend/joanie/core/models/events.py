"""
Declare and configure the models for Joanie's events
"""
import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from joanie.core import enums
from joanie.core.models.base import BaseModel

logger = logging.getLogger(__name__)


class EventContextField(models.JSONField):
    """
    EventContextField is a JSONField with validators for each type of event
    """

    def validate(self, value, model_instance):
        """
        Validate the context field
        """
        if not isinstance(value, dict):
            raise ValidationError("The context field must be a dictionary")

        event_type = model_instance.type
        if event_type == enums.EVENT_TYPE_NOTIFICATION:
            self.validate_notification(value)
        elif event_type in [
            enums.EVENT_TYPE_PAYMENT_SUCCEEDED,
            enums.EVENT_TYPE_PAYMENT_FAILED,
        ]:
            self.validate_payment_type(value)
        else:
            raise ValidationError(f"Unknown event type: {event_type}")

    def validate_notification(self, value):
        """
        Validate the context field for a notification event
        """
        if value:
            raise ValidationError("The context field must be an empty dictionary")

    def validate_payment_type(self, value):
        """
        Validate the context field for a payment type event
        """
        if "order_id" not in value:
            raise ValidationError("The context field must have an order_id")


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
    context = EventContextField(
        _("context"),
        default=dict,
    )
    type = models.CharField(
        _("type"),
        max_length=20,
        choices=lazy(lambda: enums.EVENT_TYPE_CHOICES, tuple)(),
        default=enums.EVENT_TYPE_NOTIFICATION,
    )

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")

    @classmethod
    def create_payment_succeeded_event(cls, order):
        """
        Create a payment succeeded event
        """
        return cls.objects.create(
            user=order.owner,
            level=enums.EVENT_SUCCESS,
            context={"order_id": str(order.id)},
            type=enums.EVENT_TYPE_PAYMENT_SUCCEEDED,
        )

    @classmethod
    def create_payment_failed_event(cls, order):
        """
        Create a payment failed event
        """
        return cls.objects.create(
            user=order.owner,
            level=enums.EVENT_ERROR,
            context={"order_id": str(order.id)},
            type=enums.EVENT_TYPE_PAYMENT_FAILED,
        )

    def __str__(self):
        return f"{self.user}: {self.level} {self.type}"

    def save(self, *args, **kwargs):
        """
        Validate the context field
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def get_abilities(self, user):
        """
        The user has all the abilities on their own events.
        """
        is_owner = user == self.user
        return {"delete": is_owner}
