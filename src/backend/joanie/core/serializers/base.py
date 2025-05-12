"""Base Serializer classes for the Joanie project."""

import logging

from django.conf import settings
from django.core.cache import cache

from rest_framework import serializers

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
