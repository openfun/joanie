# ruff: noqa: SLF001
"""Serializers for api."""

from rest_framework import serializers

from joanie.payment import models


class CreditCardSerializer(serializers.ModelSerializer):
    """
    CreditCard Serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    is_main = serializers.SerializerMethodField(read_only=True)

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
            "is_main",
        ]

    def get_is_main(self, instance):
        """
        Get the value `is_main` through the ownership of the card
        """
        user = self.context.get("request").user
        return instance.ownerships.get(owner=user).is_main
