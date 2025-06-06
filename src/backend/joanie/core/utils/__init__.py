"""
Utils that can be useful throughout Joanie's core app
"""

import base64
import collections.abc
import hashlib
import json
import re

from django.conf import settings
from django.utils.text import slugify

from babel.numbers import get_currency_symbol
from configurations import values
from configurations.values import ValidationMixin
from PIL import ImageFile as PillowImageFile


def remove_extra_whitespaces(text):
    """
    Remove extra whitespaces from a string.
    """
    return " ".join(text.split())


def normalize_code(code):
    """Normalize object codes to avoid duplicates."""
    return slugify(code, allow_unicode=False).upper() if code else None


def normalize_phone_number(phone_number):
    """
    Cleans up and formats the phone number by removing non-digit characters
    while preserving the '+' symbol.

    Example :
        - From "+1 (555) 123-4567"  to "+15551234567"
    """
    return "".join(char for char in phone_number if char.isdigit() or char == "+")


def merge_dict(base_dict, update_dict):
    """Utility for deep dictionary updates.

    >>> d1 = {'k1':{'k11':{'a': 0, 'b': 1}}}
    >>> d2 = {'k1':{'k11':{'b': 10}, 'k12':{'a': 3}}}
    >>> merge_dict(d1, d2)
    {'k1': {'k11': {'a': 0, 'b': 10}, 'k12':{'a': 3}}}

    """
    for key, value in update_dict.items():
        if isinstance(value, collections.abc.Mapping):
            base_dict[key] = merge_dict(base_dict.get(key, {}), value)
        else:
            base_dict[key] = value
    return base_dict


def image_to_base64(file_or_path, close=False):
    """
    Return the src string of the base64 encoding of an image represented by its path
    or file opened or not.

    Inspired by Django's "get_image_dimensions"
    """
    pil_parser = PillowImageFile.Parser()
    if hasattr(file_or_path, "read"):
        file = file_or_path
        if file.closed and hasattr(file, "open"):
            file_or_path.open()
        file_pos = file.tell()
        file.seek(0)
    else:
        try:
            # pylint: disable=consider-using-with
            file = open(file_or_path, "rb")
        except OSError:
            return ""
        close = True

    try:
        image_data = file.read()
        if not image_data:
            return ""
        pil_parser.feed(image_data)
        if pil_parser.image:
            mime_type = pil_parser.image.get_format_mimetype()
            encoded_string = base64.b64encode(image_data)
            return f"data:{mime_type:s};base64, {encoded_string.decode('utf-8'):s}"
        return ""
    finally:
        if close:
            file.close()
        else:
            file.seek(file_pos)


def file_checksum(file, chunk_size=4096):
    """
    Return the SHA256 checksum of the file.
    """
    sha256 = hashlib.sha256()
    with file.open("rb"):
        for chunk in file.chunks(chunk_size=chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()


def get_default_currency_symbol():
    """
    Return the default currency symbol based on the configured default currency.
    """
    return get_currency_symbol(settings.DEFAULT_CURRENCY)


class JSONValue(values.Value):
    """
    A custom value class based on django-configurations Value class that
    allows to load a JSON string and use it as a value.
    """

    def to_python(self, value):
        """
        Return the python representation of the JSON string.
        """
        return json.loads(value)


class LMSBackendValidator:
    """
    Validator for the LMS Backends configuration. Take a look at settings
    `JOANIE_LMS_BACKENDS` for more information.
    """

    BACKEND_REQUIRED_KEYS = ["BACKEND", "BASE_URL", "COURSE_REGEX", "SELECTOR_REGEX"]

    def __init__(self, value):
        self.__call__(value)

    def _validate_required_keys(self, backend):
        """
        Validate that the backend dictionary contains all the required keys.
        """
        for key in self.BACKEND_REQUIRED_KEYS:
            if key not in backend:
                raise ValueError(f"Missing key {key} in LMS Backend.")

    def _validate_regex_properties(self, backend):
        """
        Validate that the values of the COURSE_REGEX and SELECTOR_REGEX properties
        are valid regex strings.
        """
        course_regex = backend["COURSE_REGEX"]
        selector_regex = backend["SELECTOR_REGEX"]

        for regex in [course_regex, selector_regex]:
            try:
                re.compile(regex)
            except re.error as error:
                raise ValueError(f"Invalid regex {regex} in LMS Backend.") from error

    def _validate_backend_path_string(self, path):
        """
        Validate that the value of the BACKEND property
        is a valid python module path string.
        """
        path_regex = r"^([a-zA-Z_]+\.)*[a-zA-Z_]+$"
        if not isinstance(path, str):
            raise ValueError(f"{path} must be a string.")

        if not re.match(path_regex, path):
            raise ValueError(f"{path} must be a valid python module path string.")

    def _validate_no_update_fields_value(self, value):
        """
        Validate that the value of
        the COURSE_RUN_SYNC_NO_UPDATE_FIELDS property is a list.
        """
        if value is not None and not isinstance(value, list):
            raise ValueError("COURSE_RUN_SYNC_NO_UPDATE_FIELDS must be a list.")

    def _validate_backend(self, backend):
        self._validate_required_keys(backend)
        self._validate_regex_properties(backend)
        self._validate_backend_path_string(backend["BACKEND"])
        self._validate_no_update_fields_value(
            backend.get("COURSE_RUN_SYNC_NO_UPDATE_FIELDS")
        )

    def __call__(self, value):
        """
        Validate that the value is a list of dictionaries which describe an LMS Backends.
        And that each backend has the correct properties.
        """
        if not isinstance(value, list):
            raise ValueError("LMS Backends must be a list of dictionaries.")

        for backend in value:
            self._validate_backend(backend)


class LMSBackendsValue(ValidationMixin, values.Value):
    """
    A custom value class based on the JSONValue class that allows to load
    a JSON string and use it as a value. It also validates that the JSON
    object is a list of dictionaries which describe an LMS Backends.
    """

    validator = LMSBackendValidator

    def to_python(self, value):
        """
        Return the python representation of the JSON string.
        """
        backends = json.loads(value)
        return super().to_python(backends)


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    Used for data streaming.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value
