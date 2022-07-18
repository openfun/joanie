"""Exceptions for the badges app."""


class AuthenticationError(Exception):
    """Raised when a Badge provider credentials are not valid."""


class BadgeProviderError(Exception):
    """Generic error raised when a Badge provider encounter an exception."""
