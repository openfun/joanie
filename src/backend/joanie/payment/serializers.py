"""Serializers for api."""

from rest_framework import serializers
from rest_framework.fields import empty

from joanie.payment import models


class CreditCardSerializer(serializers.ModelSerializer):
    """
    CreditCard Serializer
    """

    id = serializers.CharField(read_only=True, required=False)

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

    def run_validation(self, data=empty):
        """
        Ignore is_main if not present in the data
        """
        validated_data = super().run_validation(data)
        if "is_main" not in data:
            del validated_data["is_main"]
        return validated_data
