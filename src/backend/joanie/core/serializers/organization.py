"""Organization Serializers"""
from rest_framework import serializers

from joanie.core import models


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Serialize all non-sensitive information about an organization
    """

    class Meta:
        model = models.Organization
        fields = ["id", "code", "title"]
        read_only_fields = ["id", "code", "title"]
