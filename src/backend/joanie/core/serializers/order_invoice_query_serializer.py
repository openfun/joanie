"""Serializers for core.api.OrderViewSet.abort Body"""

from rest_framework import serializers


class OrderInvoiceQuerySerializer(serializers.Serializer):
    reference = serializers.CharField(required=True)

    class Meta:
        fields = ["reference"]
