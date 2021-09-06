"""
Utils that can be useful throughout Joanie's core app
"""
from django.utils.text import slugify


def normalize_code(code):
    """Normalize object codes to avoid duplicates."""
    return slugify(code, allow_unicode=False).upper() if code else None
