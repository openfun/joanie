"""Serializers for core.api.OrderViewSet.create Response"""

from rest_framework import serializers

from .model_serializers import OrderSerializer, PaymentSerializer


class OrderAbortResponseSerializer(OrderSerializer):
    id = serializers.CharField(required=True)
    payment_info = PaymentSerializer(required=False)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["payment_info"]
        read_only_fields = OrderSerializer.Meta.fields + ["payment_info"]
