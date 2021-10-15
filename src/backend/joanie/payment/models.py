"""
Declare and configure models for the payment part
"""
import uuid
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CreditCard(models.Model):
    """
    Credit card model stores credit card information in order to allow
    one click payment.
    """

    uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    token = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        editable=False,
        null=False,
    )
    title = models.CharField(_("title"), max_length=100, null=True, blank=True)
    brand = models.CharField(_("brand"), max_length=40, null=True, blank=True)
    expiration_month = models.PositiveSmallIntegerField(
        _("expiration month"), validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    expiration_year = models.PositiveSmallIntegerField(_("expiration year"))
    last_numbers = models.CharField(_("last 4 numbers"), max_length=4)
    owner = models.ForeignKey(
        User,
        verbose_name=_("owner"),
        related_name="credit_cards",
        on_delete=models.CASCADE,
    )
    is_main = models.BooleanField(_("main"), default=False)

    class Meta:
        db_table = "joanie_credit_card"
        verbose_name = "credit card"
        verbose_name_plural = "credit cards"
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(is_main=True),
                fields=["owner"],
                name="unique_main_credit_card_per_user",
            )
        ]

    def clean(self):
        """
        First if this is the user's first credit card, we enforce is_main to True.
        Else if we are promoting an credit card as main, we demote the existing main credit card
        Finally prevent to demote the main credit card directly.
        """
        if not self.owner.credit_cards.exists():
            self.is_main = True
        elif self.is_main is True:
            self.owner.credit_cards.filter(is_main=True).update(is_main=False)
        elif (
            self.pk
            and self.is_main is False
            and self.owner.credit_cards.filter(is_main=True, pk=self.pk).exists()
        ):
            raise ValidationError(_("Demote a main credit card is forbidden"))

        return super().clean()

    def save(self, *args, **kwargs):
        """Enforce validation each time an instance is saved."""
        self.full_clean()
        super().save(*args, **kwargs)
