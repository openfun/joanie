"""Test utils module."""
import sys
from importlib import reload

from django.conf import settings
from django.urls import clear_url_caches


def reload_urlconf():
    """
    Enforce URL configuration reload.
    Required when using override_settings for a setting present in `joanie.urls`.
    It avoids having the url routes in cache if testing different configurations
    of accessibles routes defined if settings.DEBUG is True or False. If we don't use this
    method, you will not be able to test both configuration easily within a same class test suite.
    """
    if settings.ROOT_URLCONF in sys.modules:
        # The module is already loaded, need to reload
        reload(sys.modules[settings.ROOT_URLCONF])
        clear_url_caches()
    # Otherwise, the module will be loaded normally by Django
