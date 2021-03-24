"""
Failing LMS Backend for tests
"""

import logging
import re

from .base import BaseLMSBackend

logger = logging.getLogger(__name__)


class FailingLMSBackend(BaseLMSBackend):
    def extract_course_id(self, resource_link):
        """Extract the LMS course id from the course run url."""
        return re.match(self.configuration["COURSE_REGEX"], resource_link).group(
            "course_id"
        )

    def get_enrollment(self, username, resource_link):
        """Get enrollment status for a user on a course run given its url"""
        logger.error("Internal server error")
        return None

    def set_enrollment(self, username, resource_link):
        """Set enrollment for a user with a course run given its url."""
        logger.error("Internal server error")
        return None
