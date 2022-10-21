"""
Declare and configure the models for the customers part
"""
import uuid

import django.contrib.auth.models as auth_models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import get_supported_language_variant
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField


class User(auth_models.AbstractUser):
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

    @staticmethod
    def update_or_create_from_request_user(request_user):
        """Create user from token or update it"""
        try:
            language = get_supported_language_variant(
                request_user.language.replace("_", "-")
            )
        except LookupError:
            language = settings.LANGUAGE_CODE

        user = User.objects.update_or_create(
            username=request_user.username,
            defaults={"email": request_user.email, "language": language},
        )[0]

        return user

    # pylint: disable=arguments-differ
    def save(self, *args, **kwargs):
        """Enforcing field constraints on save.
        Parameters
        ----------
        args : list
            Passed onto parent's `save` method
        kwargs: dict
            Passed onto parent's `save` method
        """
        self.full_clean()
        super().save(*args, **kwargs)


class Address(models.Model):
    """Address model stores address information (to generate bill after payment)"""

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
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
            self.pk
            and self.is_main is False
            and self.owner.addresses.filter(is_main=True, pk=self.pk).exists()
        ):
            raise ValidationError(_("Demote a main address is forbidden"))

        return super().clean()

    def save(self, *args, **kwargs):
        """
        Enforce validation each time an instance is saved
        """
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
