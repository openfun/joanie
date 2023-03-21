"""Serializers for core.api.OrderViewSet.abort Body"""

from rest_framework import serializers

from .model_serializers import OrderSerializer, AddressSerializer


class OrderAbortBodySerializer(serializers.Serializer):
    payment_id = serializers.CharField(required=True)

    class Meta:
        fields = ["payment_id"]
