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
from django.utils.translation import get_language

import requests
from parler.utils import get_language_settings

from joanie.core import enums, utils
from joanie.core.models import DocumentImage
from joanie.core.utils import file_checksum
from joanie.lms_handler.backends.openedx import split_course_key

logger = getLogger(__name__)


def download_and_store(filename, source_path=""):
    """Download a file from edx and store it in the default storage"""
    if default_storage.exists(filename):
        return filename

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


def extract_organization_code(course_overview_id):
    """Extract the organization code from a course overview id"""
    return utils.normalize_code(split_course_key(course_overview_id)[0])


def check_language_code(language_code):
    """Return the language code"""
    if language_code not in [language[0] for language in enums.ALL_LANGUAGES]:
        language_code = "en"
    return language_code


def extract_language_code(edx_user):
    """Extract the language code from a user"""
    try:
        language = next(
            pref.value
            for pref in edx_user.user_api_userpreference
            if pref.key == "pref-lang"
        )
    except StopIteration:
        language = settings.LANGUAGE_CODE
    return get_language_settings(language).get("code")


def format_percent(current, total):
    """Format a percentage"""
    percent = (current / total) * 100
    percent = f"{percent:.3f}%" if percent < 100 else "100%"  # noqa: PLR2004
    return percent


def set_certificate_images(certificate):
    """Link Certificate to DocumentImage it is using."""
    language_code = get_language_settings(get_language()).get("code")
    certificate_context = certificate.localized_context[language_code]
    images_set = set()

    for organization in certificate_context["organizations"]:
        for key in ["logo_id", "signature_id"]:
            if image_id := organization.get(key):
                image = DocumentImage.objects.get(id=image_id)
                images_set.add(image)

    certificate.images.set(images_set)


def download_signature_image(path):
    """Download signature image from OpenEdX then store it"""
    created = False
    signature = None
    signature_image_path = path

    if signature_image_path.startswith("/"):
        signature_image_path = signature_image_path[1:]

    signature_path = download_and_store(signature_image_path)

    if signature_path:
        signature_file = default_storage.open(signature_path)
        signature_checksum = file_checksum(signature_file)
        (signature, created) = DocumentImage.objects.get_or_create(
            checksum=signature_checksum,
            defaults={"file": signature_path},
        )

    return signature, created


def update_context_signatory(context, signatory):
    """Update the certificate context with the signatory information"""
    for language, _ in settings.LANGUAGES:
        if name := signatory.get("name"):
            context[language]["organizations"][0]["representative"] = name
            context[language]["organizations"][0]["representative_profession"] = (
                signatory.get("title")
            )
        if signature_id := signatory.get("signature_id"):
            context[language]["organizations"][0]["signature_id"] = signature_id

    return context
