"""Utility functions for the OpenEdx import tasks"""
from http import HTTPStatus
from logging import getLogger

from django.conf import settings
from django.core.files.storage import default_storage

import requests

logger = getLogger(__name__)


def download_and_store(filename):
    """Download a file from edx and store it in the default storage"""
    if default_storage.exists(filename):
        return
    logger.info("Download %s", filename)
    url = f"https://{settings.EDX_DOMAIN}/media/{filename}"
    response = requests.get(url, stream=True, timeout=3)

    if response.status_code == HTTPStatus.OK:
        with default_storage.open(filename, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    output_file.write(chunk)
    else:
        logger.error("Unable to download %s", filename)
