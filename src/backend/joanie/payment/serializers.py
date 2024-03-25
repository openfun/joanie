# ruff: noqa: SLF001
"""Serializers for api."""

from rest_framework import serializers

from joanie.payment import models


class CreditCardSerializer(serializers.ModelSerializer):
    """
    CreditCard Serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    is_main = serializers.BooleanField(
        required=False,
        label=models.CreditCard._meta.get_field("is_main").verbose_name,
    )

    class Meta:
        model = models.CreditCard
        fields = [
            "id",
            "title",
            "brand",
            "expiration_month",
            "expiration_year",
            "last_numbers",
            "is_main",
        ]
        read_only_fields = [
            "id",
            "brand",
            "expiration_month",
            "expiration_year",
            "last_numbers",
        ]
