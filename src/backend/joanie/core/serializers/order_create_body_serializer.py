"""Serializers for core.api.OrderViewSet.create Body"""

from rest_framework import serializers

from .model_serializers import OrderSerializer, OrderCreateSerializer, AddressSerializer


class OrderCreateBodySerializer:
    credit_card_id = serializers.CharField(required=True)
    course = serializers.CharField(required=True)
    product = serializers.CharField(required=True)
    billing_address = AddressSerializer(required=True)

    class Meta(OrderCreateSerializer.Meta):
        fields = ["billing_address"]
