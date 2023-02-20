"""Custom template tags for the core application of Joanie."""

from django import template
from django.contrib.staticfiles import finders

from joanie.core.utils import image_to_base64

register = template.Library()


@register.simple_tag
def base64_static(path):
    """Return a static file into a base64."""
    full_path = finders.find(path)
    if full_path:
        return image_to_base64(full_path, True)
    return ""
