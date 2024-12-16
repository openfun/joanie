"""Test helpers"""

from datetime import datetime


def format_date(value: datetime) -> str | None:
    """Format a datetime to be used in a json response"""
    try:
        return value.isoformat().replace("+00:00", "Z")
    except AttributeError:
        return None


def format_date_export(value: datetime) -> str:
    """Format a datetime to be used in a csv export"""
    try:
        return value.strftime("%d/%m/%Y %H:%M:%S")
    except AttributeError:
        return ""
