"""Serializers for core.api.OrderViewSet.abort Body"""

from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    details = serializers.CharField(required=True)

    class Meta:
        fields = ["details"]
