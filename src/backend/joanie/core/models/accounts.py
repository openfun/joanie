"""
Declare and configure the models for the customers part
"""
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

    class Meta:
        db_table = "joanie_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)

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
    )
    is_main = models.BooleanField(_("main"), default=False)

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
            )
        ]

    def __str__(self):
        return f"{self.address}, {self.postcode} {self.city}, {self.country}"

    def clean(self):
        """
        First if this is the user's first address, we enforce is_main to True.
        Else if we are promoting an address as main, we demote the existing main address
        Finally prevent to demote the main address directly.
        """
        if not self.owner.addresses.exists():
            self.is_main = True
        elif self.is_main is True:
            self.owner.addresses.filter(is_main=True).update(is_main=False)
        elif (
            self.created_on
            and self.is_main is False
            and self.owner.addresses.filter(is_main=True, pk=self.pk).exists()
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
