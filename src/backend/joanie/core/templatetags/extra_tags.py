"""Custom template tags for the core application of Joanie."""

from django import template
from django.contrib.staticfiles import finders
from django.utils.translation import gettext as _

from joanie.core.utils import image_to_base64

register = template.Library()


@register.simple_tag
def base64_static(path):
    """Return a static file into a base64."""
    full_path = finders.find(path)
    if full_path:
        return image_to_base64(full_path, True)
    return ""


@register.filter
def join_and(items: list):
    """A template tag filter to join a list of items in human-readable way."""
    comma_join_threshold = 2
    if len(items) > comma_join_threshold:
        return _("{:s} and {:s}").format(
            ", ".join(map(str, items[:-1])), str(items[-1])
        )

    return _(" and ").join(map(str, items))


@register.filter
def list_key(items: list[dict], key: str):
    """
    A template tag filter to get a list of values from a list of dictionaries.
    """
    return [item[key] for item in items]
