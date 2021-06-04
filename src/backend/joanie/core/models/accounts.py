"""
Declare and configure the models for the customers part
"""
import uuid

import django.contrib.auth.models as auth_models
from django.core import validators
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
    name = models.CharField(_("name"), max_length=100)
    address = models.CharField(_("address"), max_length=255)
    postcode = models.CharField(_("postcode"), max_length=50)
    city = models.CharField(_("city"), max_length=255)
    country = CountryField(_("country"))
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


class CreditCard(models.Model):
    """Credit card model to allow to save user credit cards"""

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    name = models.CharField(_("name"), max_length=100)
    # token returned by service payment backend
    token = models.CharField(_("token"), max_length=128)
    expiration_date = models.DateField(_("expiration date"), db_index=True)
    owner = models.ForeignKey(
        User,
        verbose_name=_("user"),
        related_name="creditcards",
        on_delete=models.CASCADE,
    )
    last_numbers = models.CharField(
        _("last numbers"),
        max_length=4,
        validators=[
            validators.RegexValidator("^[0-9]{4}$", _("Enter a valid value (4 digits)"))
        ],
    )
    main = models.BooleanField(_("main"), default=False)

    class Meta:
        db_table = "joanie_credit_card"
        verbose_name = _("Credit card")
        verbose_name_plural = _("Credit cards")

    def __str__(self):
        return f"{self.owner} - ****{self.last_numbers}"

    def save(self, *args, **kwargs):
        # no more one main=True per Owner
        main_credit_cards = self.owner.creditcards.filter(main=True)
        if self.main and main_credit_cards:
            main_credit_cards.update(main=False)
        super().save(*args, **kwargs)
