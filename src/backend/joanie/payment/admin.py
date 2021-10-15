"""
Payment application admin
"""
from django.contrib import admin

from . import models


@admin.register(models.CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    """Admin class for the credit card model."""

    list_display = ("owner", "title", "numbers", "expiration_date", "is_main")

    @staticmethod
    def numbers(credit_card):
        """
        Return credit_card.last_numbers into a human-readable format
        """
        return f"XXXX XXXX XXXX {credit_card.last_numbers}"

    @staticmethod
    def expiration_date(credit_card):
        """
        Retrieve a human-readable expiration date from
        expiration_month and expiration_year
        """

        return f"{credit_card.expiration_month:02d}/{credit_card.expiration_year:02d}"
