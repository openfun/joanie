"""Custom template tags for the core application of Joanie."""

import math

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.defaultfilters import date
from django.utils.dateparse import parse_datetime
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from babel.core import Locale
from babel.numbers import format_currency
from parler.utils import get_language_settings
from stockholm import Money
from timedelta_isoformat import timedelta as timedelta_isoformat

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


@register.filter
def iso8601_to_date(value: str, arg: str = None) -> str:
    """
    Custom tag filter to format an ISO 8601 datetime string into
    a formatted date string.

    Parameter:
        - `value`: An ISO8601 datetime string
        - `arg`: Date format
                 https://docs.djangoproject.com/en/5.0/ref/templates/builtins/#date

    Usage in Django HTML template (after loading the extra tags) :
        - {{ datetime_string|iso8601_to_date:<DATETIME_FORMAT>}}

    """
    if not isinstance(value, str):
        return ""

    datetime = parse_datetime(value)
    return date(datetime, arg)


@register.filter
def iso8601_to_duration(duration, unit):
    """
    Custom tag filter to convert ISO 8601 duration to a specified time unit.
    The result is rounded-up using the ceil() method from Python's math
    module.

    Parameter :
        - `duration`: the ISO 8601 duration value declared in the HTML template
        - `unit` : the desired time unit, it can be "seconds", "minutes", or "hours".

    Usage in Django HTML template (after loading the extra tags) :
        - {{ course.effort|iso8601_to:"seconds"}} : returns in seconds
        - {{ course.effort|iso8601_to:"minutes"}} : returns in minutes
        - {{ course.effort|iso8601_to:"hours"}} : returns in hours
    """
    selected_time_unit = {
        "seconds": 1,
        "minutes": 60,
        "hours": 3600,
    }
    if not isinstance(duration, str):
        return ""

    try:
        course_effort_timedelta = timedelta_isoformat.fromisoformat(duration)
    except ValueError:
        return ""

    return math.ceil(course_effort_timedelta.total_seconds() / selected_time_unit[unit])


@register.filter
def format_currency_with_symbol(value: Money):
    """
    Formats the given value depending on the country's way to format an amount
    of money and it adds the appropriate currency symbol.
    It uses the `DEFAULT_CURRENCY` and the active language (`LANGUAGE_CODE`) setting to render the
    amount accordingly.

    Example :
        - If you use `fr-fr` for LANGUAGE_CODE : 200,00 €
        - If you use `en-us` for LANGUAGE_CODE : €200.00
    """
    parts = str(value).split()
    amount = parts[0]
    return format_currency(
        amount,
        settings.DEFAULT_CURRENCY,
        locale=Locale.parse(get_language_settings(get_language()).get("code"), sep="-"),
    )
