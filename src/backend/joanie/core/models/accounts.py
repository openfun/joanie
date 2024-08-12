"""
Declare and configure the models for the customers part
"""

import logging

import django.contrib.auth.models as auth_models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField
from rest_framework_simplejwt.settings import api_settings

from joanie.core.authentication import get_user_dict
from joanie.core.models.base import BaseModel
from joanie.core.utils import normalize_phone_number
from joanie.core.utils.newsletter.subscription import (
    set_commercial_newsletter_subscription,
)

logger = logging.getLogger(__name__)


class User(BaseModel, auth_models.AbstractUser):
    """User model which follow courses or manage backend (is_staff)"""

    language = models.CharField(
        default=settings.LANGUAGE_CODE,
        max_length=10,
        choices=lazy(lambda: settings.LANGUAGES, tuple)(),
        verbose_name=_("language"),
        help_text=_("Language of the user"),
    )

    password = models.CharField(
        max_length=128,
        default="!",
        verbose_name=_("password"),
    )

    phone_number = models.CharField(
        verbose_name=_("Phone number"),
        max_length=40,
        blank=True,
        null=True,
    )

    has_subscribed_to_commercial_newsletter = models.BooleanField(
        verbose_name=_("has subscribed to commercial newsletter"),
        default=False,
    )

    class Meta:
        db_table = "joanie_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_has_subscribed_to_commercial_newsletter = (
            self.has_subscribed_to_commercial_newsletter
        )

    def __str__(self):
        return self.username

    def clean(self):
        """
        Normalize the `phone_number` value for consistency in database.
        """
        if phone_number := self.phone_number:
            self.phone_number = normalize_phone_number(phone_number)
        return super().clean()

    def save(self, *args, **kwargs):
        """
        Enforce validation each time an instance is saved and trigger the
        commercial newsletter subscription task if the user has subscribed to
        """
        self.full_clean()

        is_creating = self.created_on is None

        super().save(*args, **kwargs)

        if is_creating and self.has_subscribed_to_commercial_newsletter:
            # The user is being created and has subscribed to the newsletter
            logger.info(
                "New user %s has subscribed to the commercial newsletter", self.id
            )
            set_commercial_newsletter_subscription.delay(self.to_dict())
        if (
            self.has_subscribed_to_commercial_newsletter
            != self.last_has_subscribed_to_commercial_newsletter
        ):
            # The user has changed their subscription status
            logger.info(
                "User %s has changed their subscription status to %s",
                self.id,
                self.has_subscribed_to_commercial_newsletter,
            )
            self.last_has_subscribed_to_commercial_newsletter = (
                self.has_subscribed_to_commercial_newsletter
            )
            set_commercial_newsletter_subscription.delay(self.to_dict())
        else:
            logger.info("User %s has not changed their subscription status", self.id)

    def update_from_token(self, token):
        """Update user from token token."""
        values = get_user_dict(token)
        for key, value in values.items():
            if value != getattr(self, key):
                User.objects.filter(
                    **{
                        api_settings.USER_ID_FIELD: getattr(
                            self, api_settings.USER_ID_FIELD
                        )
                    }
                ).update(**values)
                break

    def get_abilities(self, user):
        """
        Compute and return abilities for the user taking into account their
        roles on other objects.
        """
        is_self = user == self
        abilities = {
            "delete": False,
            "get": is_self,
            "patch": is_self,
            "put": is_self,
        }

        has_course_access = user.course_accesses.exists()
        has_organization_access = user.organization_accesses.exists()
        abilities.update(
            {
                "has_course_access": has_course_access,
                "has_organization_access": has_organization_access,
            }
        )

        return abilities


class Address(BaseModel):
    """Address model stores address information (to generate bill after payment)"""

    title = models.CharField(_("title"), max_length=100)
    address = models.CharField(_("address"), max_length=255)
    postcode = models.CharField(_("postcode"), max_length=50)
    city = models.CharField(_("city"), max_length=255)
    country = CountryField(_("country"))
    first_name = models.CharField(_("first name"), max_length=255)
    last_name = models.CharField(_("last name"), max_length=255)
    owner = models.ForeignKey(
        User,
        verbose_name=_("owner"),
        related_name="addresses",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        to="core.Organization",
        verbose_name=_("organization"),
        related_name="addresses",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_main = models.BooleanField(_("main"), default=False)
    is_reusable = models.BooleanField(_("reusable"), default=False)

    class Meta:
        db_table = "joanie_address"
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        ordering = ["-created_on"]
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(is_main=True),
                fields=["owner"],
                name="unique_main_address_per_user",
            ),
            models.UniqueConstraint(
                condition=models.Q(is_main=True),
                fields=["organization"],
                name="unique_main_address_per_organization",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(organization__isnull=False, owner__isnull=True)
                    | models.Q(organization__isnull=True, owner__isnull=False)
                ),
                name="either_owner_or_organization",
                violation_error_message=_("Either owner or organization must be set."),
            ),
            models.CheckConstraint(
                check=(models.Q(is_reusable=True) | models.Q(is_main=False)),
                name="main_address_must_be_reusable",
                violation_error_message=_("Main address must be reusable."),
            ),
            models.UniqueConstraint(
                fields=[
                    "owner",
                    "address",
                    "postcode",
                    "city",
                    "country",
                    "first_name",
                    "last_name",
                ],
                name="unique_address_per_user",
            ),
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "address",
                    "postcode",
                    "city",
                    "country",
                    "first_name",
                    "last_name",
                ],
                name="unique_address_per_organization",
            ),
        ]

    def __str__(self):
        return f"{self.address}, {self.postcode} {self.city}, {self.country}"

    def clean(self):
        """
        If the address is reusable, we enforce some rules:
        If this is the user's or the organization's first address, we set 'is_main' to True.
        If we are promoting an address as the main one, we demote the existing main address.
        Finally, we prevent directly demoting the main address.
        """
        if self.is_reusable:
            instance = self.owner or self.organization
            if not instance.addresses.exists():
                self.is_main = True
            elif self.is_main:
                instance.addresses.filter(is_main=True).update(is_main=False)
            elif (
                self.created_on
                and instance.addresses.filter(is_main=True, pk=self.pk).exists()
            ):
                raise ValidationError(_("Demote a main address is forbidden"))

        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Recipient fullname"""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_address(self):
        """Full address to display"""
        return f"{self.address}\n{self.postcode} {self.city}\n{self.country.name}"
