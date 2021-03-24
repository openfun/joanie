"""
Dummy LMS Backend for tests
"""

import re

from django.core.cache import cache
from django.utils import timezone

from joanie.core.factories import CourseRunFactory

from .base import BaseLMSBackend


class DummyLMSBackend(BaseLMSBackend):
    """Dummy LMS Backend to mock behavior of a LMS using cache."""

    @staticmethod
    def get_cache_key(username, course_id):
        """Process a cache key related to the username and the course_id provided."""
        return f"dummy_lms_backend_enrollment_{username:s}_{course_id:s}"

    def extract_course_id(self, resource_link):
        return re.match(self.configuration["COURSE_REGEX"], resource_link).group(
            "course_id"
        )

    def get_enrollment(self, username, resource_link):
        """
        Get fake enrollment from cache for a user on a course run given its resource_link.
        """
        course_id = self.extract_course_id(resource_link)
        course_run = CourseRunFactory.build()
        cache_key = self.get_cache_key(username, course_id)

        if cache.get(cache_key):
            return {
                "created": timezone.now().isoformat(),  # 2020-07-21T17:42:04.675422Z
                "mode": "audit",
                "is_active": True,
                "course_details": {
                    "course_id": course_id,
                    "course_name": f"Course: {course_id:s}",
                    "enrollment_start": course_run.enrollment_start.isoformat(),
                    "enrollment_end": course_run.enrollment_end.isoformat(),
                    "course_start": course_run.start.isoformat(),
                    "course_end": course_run.end.isoformat(),
                    "invite_only": False,
                    "course_modes": [
                        {
                            "slug": "audit",
                            "name": "Audit",
                            "min_price": 0,
                            "suggested_prices": "",
                            "currency": "eur",
                            "expiration_datetime": None,
                            "description": None,
                            "sku": None,
                            "bulk_sku": None,
                        }
                    ],
                },
                "user": username,
            }

        return None

    def set_enrollment(self, username, resource_link, active=True):
        """
        Set fake enrollment to cache for a user with a course run given
        its resource_link and its active state.
        """
        course_id = self.extract_course_id(resource_link)
        cache_key = self.get_cache_key(username, course_id)

        if active:
            cache.set(cache_key, True)
        else:
            cache.delete(cache_key)

        return self.get_enrollment(username, resource_link)
