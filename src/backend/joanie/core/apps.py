"""Joanie Core application"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """Configuration class for the joanie core app."""

    name = "joanie.core"
    verbose_name = _("Joanie's core application")

    # pylint: disable=import-outside-toplevel, unused-import
    def ready(self):
        """Import enrollment post delete receiver."""
        from .models.products import enrollment_post_delete_receiver  # noqa: F401,
