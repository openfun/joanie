"""
Utils that can be useful throughout Joanie's core app
"""
import base64
import collections.abc

from django.utils.text import slugify

from PIL import ImageFile as PillowImageFile


def normalize_code(code):
    """Normalize object codes to avoid duplicates."""
    return slugify(code, allow_unicode=False).upper() if code else None


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
