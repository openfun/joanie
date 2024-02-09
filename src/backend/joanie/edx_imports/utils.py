"""Utility functions for the Open edX import tasks"""
# pylint: disable=too-many-statements,not-callable,too-many-locals
# ruff: noqa: PLR0915,SLF001

from datetime import datetime
from http import HTTPStatus
from logging import getLogger
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.timezone import make_aware as django_make_aware

import requests
from parler.utils import get_language_settings

from joanie.core import enums, utils
from joanie.lms_handler.backends.openedx import split_course_key

logger = getLogger(__name__)


def download_and_store(filename, source_path=""):
    """Download a file from edx and store it in the default storage"""
    if default_storage.exists(filename):
        return default_storage.path(filename)

    logger.info("Download %s", filename)
    url = f"https://{settings.EDX_DOMAIN}/"
    if source_path:
        url += f"{source_path}/"
    url += filename

    response = requests.get(url, stream=True, timeout=3)

    if response.status_code == HTTPStatus.OK:
        return default_storage.save(filename, response.raw)

    logger.error("Unable to download %s", filename)
    return None


def make_date_aware(date: datetime) -> datetime:
    """Make a datetime aware using the Open edX timezone"""
    return django_make_aware(date, ZoneInfo(key=settings.EDX_TIME_ZONE))


def format_date(value: datetime) -> str | None:
    """Format a naive date to isoformat and make it aware"""
    try:
        return make_date_aware(value).isoformat()
    except AttributeError:
        return None


def extract_course_number(course_overview_id):
    """Extract the course number from a course overview id"""
    return utils.normalize_code(split_course_key(course_overview_id)[1])


def check_language_code(language_code):
    """Return the language code"""
    if language_code not in [language[0] for language in enums.ALL_LANGUAGES]:
        language_code = "en"
    return language_code


def extract_language_code(edx_user):
    """Extract the language code from a user"""
    language = next(
        pref.value
        for pref in edx_user.user_api_userpreference
        if pref.key == "pref-lang"
    )
    return get_language_settings(language).get("code")
