"""Custom serializer fields."""
from easy_thumbnails.alias import aliases
from easy_thumbnails.files import ThumbnailerImageFieldFile
from rest_framework import serializers
from rest_framework.fields import DurationField
from timedelta_isoformat import timedelta as timedelta_isoformat


class ImageDetailField(serializers.ImageField):
    """Custom serializer ImageField to return image details as dict."""

    def get_absolute_url(self, value):
        """Build absolute url from value."""
        try:
            url = value.url
        except AttributeError:
            return None
        request = self.context.get("request", None)
        if request is not None:
            return request.build_absolute_uri(url)

        return url

    def to_representation(self, value):
        """Return image filename, url and dimensions."""
        if not value:
            return None

        return {
            "filename": value.name,
            "height": value.height,
            "width": value.width,
            "src": self.get_absolute_url(value),
            "size": value.size,
        }


class ThumbnailDetailField(ImageDetailField):
    """
    Custom serializer field for ThumbnailImageField to return thumbnail details as dict.
    """

    def to_representation(self, value):
        """Return thumbnail filename, src, srcset and dimensions."""
        representation = super().to_representation(value)
        is_thumbnail = isinstance(value, ThumbnailerImageFieldFile)

        if not representation:
            return None

        if is_thumbnail:
            # - src
            representation["src"] = self.get_absolute_url(
                value.get_thumbnail({"size": (value.width, value.height)})
            )

            # - srcset
            all_options = aliases.all(value, include_global=False) or aliases.all(value)
            if all_options:
                srcset = []
                for descriptor, options in all_options.items():
                    thumbnail = value.get_thumbnail(options)
                    url = self.get_absolute_url(thumbnail)
                    srcset.append(f"{url} {descriptor}")
                representation["srcset"] = ", ".join(srcset)

        return representation


class ISO8601DurationField(DurationField):
    """
    Custom serializer DurationField to return the value into ISO 8601 format.
    When it comes to internal value, it returns the ISO 8601 format value
    into python's datetime.timedelta.
    """

    def to_representation(self, value):
        """
        Return the value of timedelta type into ISO 8601 format.
        """
        return timedelta_isoformat(seconds=value.total_seconds()).isoformat()
