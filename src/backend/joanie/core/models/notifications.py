"""
Declare and configure the models for the notification part
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from . import User
from .base import BaseModel


class Notification(BaseModel):
    """
    Notification model define a notification about an action on a object instance according a
    subject instance.

    notif_subject: [GenericForeignKey]
        Defined using notif_subject_ctype [ContentType] and notif_subject_id [uuid]
        It represents the user's subject that he want to be notified about.
        It can be a user course wish or a user course enrollment.

    notif_object: [GenericForeignKey]
        Defined using notif_object_ctype [ContentType] and notif_object_id [uuid]
        It represents the object that generate the notification according the user's subject
        It can be a course run, a product or the relation between a product and an course.

    action: [CharField with NOTIF_ACTIONS choices]
        It represents the action done on the object that generate the notification
        The action's values are
            "ADD": the object has been add in a m2m relationship
            "CREATE": the object has been create

    notif_type: [CharField with NOTIF_TYPES choices]
        It's the type of the notification
        It can be an email or a dashboard notification (not implemented yet)

    notified_at: [DateTimeField]
        It's the DatiTime when the notification has been sent to the owner.
        If the value is None, the notification has not been sent yet.

    owner: [User]
        It's the User that received or will receive the notification.
    """

    NOTIF_ACTION_ADD = "ADD"
    NOTIF_ACTION_CREATE = "CREATE"

    NOTIF_ACTIONS = (
        (NOTIF_ACTION_ADD, _("added")),
        (NOTIF_ACTION_CREATE, _("created")),
    )

    NOTIF_TYPE_EMAIL = "EMAIL"

    NOTIF_TYPES = (
        (NOTIF_TYPE_EMAIL, _("Send an email")),
    )

    notif_subject_ctype_limit = models.Q(app_label='core', model='coursewish') \
                                | models.Q(app_label='core', model='enrollment')
    notif_subject_ctype = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="subject_ctype_of_notifications",
        limit_choices_to=notif_subject_ctype_limit
    )
    notif_subject_id = models.UUIDField()
    notif_subject = GenericForeignKey('notif_subject_ctype', 'notif_subject_id')

    notif_object_ctype_limit = models.Q(app_label='core', model='producttargetcourserelation') \
                               | models.Q(app_label='core', model='courserun') \
                               | models.Q(app_label='core', model='product')
    notif_object_ctype = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="object_ctype_of_notifications",
        limit_choices_to=notif_object_ctype_limit
    )
    notif_object_id = models.UUIDField()
    notif_object = GenericForeignKey('notif_object_ctype', 'notif_object_id')

    action = models.CharField(
        _("Action on the object of notification"),
        choices=NOTIF_ACTIONS,
        max_length=10,
        default=NOTIF_ACTION_CREATE
    )

    notif_type = models.CharField(
        _("Type of notification"),
        choices=NOTIF_TYPES,
        max_length=10,
        default=NOTIF_TYPE_EMAIL
    )

    notified_at = models.DateTimeField(
        verbose_name=_("Notified at"),
        help_text=_("date and time when the notification has been sent to the owner"),
        blank=True,
        null=True,
        editable=False,
    )

    owner = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        db_table = "joanie_notification"
        ordering = ("owner", "notified_at")
        verbose_name = _(
            "Notification"
        )
        verbose_name_plural = _(
            "Notifications"
        )

    def __str__(self):
        if self.notified_at:
            return (
                f"'{self.owner}' has been notified about "
                f"'{self.notif_object}' according to '{self.notif_subject}' at '{self.notified_at}'"
            )
        return (
            f"'{self.owner}' hasn't been notified about "
            f"'{self.notif_object}' according to '{self.notif_subject}' yet"
        )
