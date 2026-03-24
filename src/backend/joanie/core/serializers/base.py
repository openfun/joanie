"""Base Serializer classes for the Joanie project."""

import csv
import logging

from django.conf import settings
from django.core.cache import cache

from rest_framework import serializers

from joanie.core.utils import Echo

logger = logging.getLogger(__name__)


class CachedModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that caches the serialized data.
    """

    def to_representation(self, instance):
        """
        Cache the serializer representation for the current instance.
        """
        cache_key = instance.get_cache_key(
            is_language_sensitive=True,
            prefix=self.__class__.__name__,
        )
        representation = cache.get(cache_key)

        if representation is None:
            representation = super().to_representation(instance)
            cache_ttl = getattr(
                self.Meta,  # pylint: disable=no-member
                "cache_ttl",
                settings.JOANIE_SERIALIZER_DEFAULT_CACHE_TTL,
            )
            logger.debug(
                "Setting cache for %s: %s (cache_ttl=%s)",
                self.__class__.__name__,
                cache_key,
                cache_ttl,
            )
            cache.set(cache_key, representation, cache_ttl)
        else:
            logger.debug(
                "Cache hit for %s: %s (cache_ttl=%s)",
                self.__class__.__name__,
                cache_key,
                settings.JOANIE_SERIALIZER_DEFAULT_CACHE_TTL,
            )

        return representation


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer used to format error responses.
    """

    details = serializers.CharField(required=True)

    class Meta:
        fields = ["details"]

    def create(self, validated_data):
        """Abstract method that should be implemented."""
        raise NotImplementedError()

    def update(self, instance, validated_data):
        """Abstract method that should be implemented."""
        raise NotImplementedError()


class CSVExportListSerializer(serializers.ListSerializer):
    """
    Serializer for exporting a list of objects to a CSV stream.
    """

    def update(self, instance, validated_data):
        """
        Only there to avoid a NotImplementedError.
        """
        return instance

    def csv_stream(self):
        """
        Return a CSV stream of the serialized data.
        """
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        yield writer.writerow(self.child.headers)
        for obj in self.instance:
            row = self.child.to_representation(obj)
            yield writer.writerow(row.values())
