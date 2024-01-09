"""
Backend to connect Joanie to Moodle LMS
"""
import logging
from urllib.parse import parse_qs, urlparse

from moodle import Moodle
from moodle.exception import EmptyResponseException

from .base import BaseLMSBackend

logger = logging.getLogger(__name__)


class MoodleLMSBackend(BaseLMSBackend):
    """LMS Backend to connect Joanie to Moodle LMS"""

    def __init__(self, configuration, *args, **kwargs):
        """Attach configuration to the LMS backend instance."""
        super().__init__(configuration, *args, **kwargs)
        self.base_url = self.configuration["BASE_URL"]
        self.token = self.configuration["API_TOKEN"]
        self.moodle = Moodle(self.base_url, self.token)

    def build_url(self, function):
        """Build a Moodle API url."""
        return f"{self.base_url}?wstoken={self.token}&wsfunction={function}&moodlewsrestformat=json"

    def extract_course_id(self, resource_link):
        """Extract the LMS course id from the course run url."""
        parsed_url = urlparse(resource_link)
        query_parameters = parse_qs(parsed_url.query)
        return int(query_parameters.get("id")[0])

    def get_enrollment(self, username, resource_link):
        """
        Retrieve an enrollment according to a username and a resource_link.
        """
        enrollments = self.get_enrollments(resource_link)
        if not enrollments:
            logger.error("No enrollments found for course run %s", resource_link)
            return None
        filtered_enrollments = filter(
            lambda enrollment: enrollment.get("username") == username, enrollments
        )
        try:
            return next(filtered_enrollments)
        except StopIteration:
            logger.error(
                "No enrollment found for user %s in course run %s",
                username,
                resource_link,
            )
            return None

    def get_enrollments(self, resource_link):
        """Retrieve enrollments according to a resource_link."""
        course_id: int = self.extract_course_id(resource_link)
        try:
            return self.moodle(
                "core_enrol_get_enrolled_users", courseid=course_id, options=None
            )
        except EmptyResponseException as e:
            logger.error("Moodle error while retrieving enrollments: %s", e)
            return None

    def set_enrollment(self, enrollment):
        """Activate/deactivate an enrollment."""

    def get_grades(self, username, resource_link):
        """Get user's grades for a course run given its url."""
