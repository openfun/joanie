"""Custom serializer fields."""
from rest_framework import serializers


class ImageDetailField(serializers.ImageField):
    """Custom serializer ImageField to return image details as dict."""

    def to_representation(self, value):
        """Return image filename, url and dimensions."""
        if value:
            # ImageField returns the file url containing the hostname, we want to keep
            # this behavior.
            url_with_hostname = super().to_representation(value)
            return {
                "filename": value.name,
                "url": url_with_hostname,
                "height": value.height,
                "width": value.width,
            }
        return None
