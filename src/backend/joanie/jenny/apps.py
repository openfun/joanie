"""Joanie Jenny application"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class JennyConfig(AppConfig):
    """Configuration class for the joanie core app."""

    name = "joanie.jenny"
    verbose_name = _("Joanie's jenny application")
