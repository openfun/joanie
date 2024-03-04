"""Module containing specific storages."""

from django.conf import settings

from storages.backends.s3 import S3Storage


# pylint: disable=abstract-method
class JoanieEasyThumbnailS3Storage(S3Storage):
    """
    Storage used by easy thumbnail and defined in the settings THUMBNAIL_DEFAULT_STORAGE.
    It uses the settings shared with the default storage. Only the location is redefined.
    """

    location = settings.THUMBNAIL_STORAGE_S3_LOCATION
