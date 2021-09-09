"""
Declare and configure the models for the customers part
"""
import uuid

import django.contrib.auth.models as auth_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField


class User(auth_models.AbstractUser):
    """User model which follow courses or manage backend (is_staff)"""

    class Meta:
        db_table = "joanie_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.username


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
    fullname = models.CharField(_("full name"), max_length=255)
    owner = models.ForeignKey(
        User,
        verbose_name=_("owner"),
        related_name="addresses",
        on_delete=models.CASCADE,
    )
    main = models.BooleanField(_("main"), default=False)

    class Meta:
        db_table = "joanie_address"
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(main=True),
                fields=["owner"],
                name="unique_main_address_per_user",
            )
        ]

    def __str__(self):
        return f"{self.address}, {self.postcode} {self.city}, {self.country}"

    def save(self, *args, **kwargs):
        # no more one main=True per Owner
        main_addresses = self.owner.addresses.filter(main=True)
        if self.main and main_addresses:
            main_addresses.update(main=False)
        super().save(*args, **kwargs)

    def get_full_address(self):
        """Full address to display"""
        return f"{self.address}\n{self.postcode} {self.city}\n{self.country.name}"
