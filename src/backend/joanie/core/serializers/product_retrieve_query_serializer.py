"""Serializers for core.api.OrderViewSet.abort Body"""

from rest_framework import serializers


class ProductRetrieveQuerySerializer(serializers.Serializer):
    course = serializers.CharField(required=True)

    class Meta:
        fields = ["course"]
