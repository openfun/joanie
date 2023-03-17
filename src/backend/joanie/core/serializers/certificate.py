"""Certificate serializers"""
from django.utils.translation import get_language

from rest_framework import serializers

from joanie.core import models

from .certificate_definition import CertificationDefinitionSerializer
from .order import CertificateOrderSerializer


class CertificateSerializer(serializers.ModelSerializer):
    """
    Certificate model serializer
    """

    id = serializers.CharField(read_only=True, required=False)
    certificate_definition = CertificationDefinitionSerializer(read_only=True)
    order = CertificateOrderSerializer(read_only=True)

    class Meta:
        model = models.Certificate
        fields = ["id", "certificate_definition", "issued_on", "order"]
        read_only_fields = ["id", "certificate_definition", "issued_on", "order"]

    def get_context(self, certificate):
        """
        Compute the serialized value for the "context" field.
        """
        language = self.context["request"].LANGUAGE_CODE or get_language()
        return certificate.localized_context[language]
