"""Test helpers"""

from datetime import datetime


def format_date(value: datetime) -> str | None:
    """Format a datetime to be used in a json response"""
    try:
        return value.isoformat().replace("+00:00", "Z")
    except AttributeError:
        return None
