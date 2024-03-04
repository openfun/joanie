"""LMS Handler"""

import re

from django.conf import settings
from django.utils.module_loading import import_string


class LMSHandler:
    """
    Class to handle LMS backends.

    Actions on a particular course run are automatically routed to the
    LMS handling this course via the `SELECTOR_REGEX` configured for each LMS.
    """

    @staticmethod
    def get_all_lms():
        """
        Return all LMS Backends

        Offer the possibility to iterate over all LMS used to retrieve, for example, same kind of
        information accross several LMS.
        """
        return [
            import_string(lms_configuration["BACKEND"])(lms_configuration)
            for lms_configuration in settings.JOANIE_LMS_BACKENDS
        ]

    @staticmethod
    def select_lms(resource_link):
        """
        Select and return the first LMS backend matching the url passed in argument.

        Return an LMS Backend instance according to its course run url.
        Default to None if no LMS has been found.
        """
        if resource_link is None:
            return None

        for lms_configuration in settings.JOANIE_LMS_BACKENDS:
            if re.match(lms_configuration.get("SELECTOR_REGEX", r".*"), resource_link):
                return import_string(lms_configuration["BACKEND"])(lms_configuration)

        return None
