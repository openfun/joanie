"""
Backend to connect Joanie to Moodle LMS
"""

import logging
from urllib.parse import parse_qs, urlparse

from django.conf import settings

from moodle import Moodle
from moodle.exception import (
    EmptyResponseException,
    MoodleException,
    NetworkMoodleException,
)

from joanie.core.exceptions import EnrollmentError, GradeError

from .base import BaseLMSBackend

logger = logging.getLogger(__name__)


class MoodleStudentRoleException(Exception):
    """Raised when the student role is not found in Moodle."""


class MoodleUserException(Exception):
    """Raised when a user is not found in Moodle."""


class MoodleUserCreateException(Exception):
    """Raised when a user creation fails in Moodle."""


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
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error("Moodle error while retrieving enrollments: %s", e)
            return None

    def get_roles(self):
        """Retrieve roles."""
        try:
            return self.moodle("local_wsgetroles_get_roles")
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error(e)
            return []

    def student_role_id(self):
        """Retrieve student role id."""
        roles = self.get_roles()
        for role in roles:
            if role.get("shortname") == "student":
                return role.get("id")
        raise MoodleStudentRoleException("Student role not found in Moodle")

    # pylint: disable=invalid-name
    def get_user_id(self, username):
        """Retrieve user id."""
        username = username.lower()
        criteria = {"key": "username", "value": username}
        try:
            res = self.moodle("core_user_get_users", criteria=[criteria])
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error("Moodle error while retrieving user %s: %s", username, e)
            raise MoodleUserException() from e
        try:
            # username is unique in Moodle
            user_id = res.get("users", [])[0].get("id")
        except IndexError as e:
            logger.info("User %s not found in Moodle", username)
            raise MoodleUserException() from e
        return user_id

    def create_user(self, user):
        """Create a user."""
        user.username = user.username.lower()
        user_data = {
            "username": user.username,
            "firstname": user.first_name,
            "lastname": user.last_name or ".",
            "email": user.email,
            "auth": settings.MOODLE_AUTH_METHOD,
        }
        try:
            return self.moodle("core_user_create_users", users=[user_data])[0]
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error("Moodle error while creating user %s: %s", user.username, e)
            raise MoodleUserCreateException() from e

    def set_enrollment(self, enrollment):
        """Activate/deactivate an enrollment."""
        try:
            role_id = self.student_role_id()
        except MoodleStudentRoleException as e:
            logger.error("Moodle error while retrieving student role: %s", e)
            raise EnrollmentError() from e

        try:
            user_id = self.get_user_id(enrollment.user.username)
        except MoodleUserException as e:
            if not enrollment.is_active:
                raise EnrollmentError() from e
            user_created = self.create_user(enrollment.user)
            user_id = user_created.get("id")

        course_id = self.extract_course_id(enrollment.course_run.resource_link)
        moodle_enrollment = {
            "courseid": course_id,
            "userid": user_id,
            "roleid": role_id,
        }
        try:
            if enrollment.is_active:
                self.moodle.enrol.manual.enrol_users([moodle_enrollment])
            else:
                self.moodle.enrol.manual.unenrol_users([moodle_enrollment])
        except (MoodleException, NetworkMoodleException) as e:
            logger.error(
                "Moodle error while %s user %s (userid: %s, roleid %s, courseid %s): %s: %s",
                "enrolling" if enrollment.is_active else "unenrolling",
                enrollment.user.username,
                user_id,
                role_id,
                course_id,
                e,
                e.exception if hasattr(e, "exception") else "",
            )
            raise EnrollmentError() from e
        except EmptyResponseException:
            # No response is returned from Moodle API when enrolling or unenrolling a user
            pass
        return True

    def get_grades(self, username, resource_link):
        """Get user's grades for a course run given its url."""
        try:
            user_id = self.get_user_id(username)
        except MoodleUserException as e:
            raise GradeError() from e
        course_id = self.extract_course_id(resource_link)

        try:
            completion = self.moodle.core.completion.get_course_completion_status(
                course_id, user_id
            )
            return {"passed": completion.completionstatus.completed}

        except (MoodleException, EmptyResponseException, NetworkMoodleException) as e:
            logger.error(
                "Moodle error while retrieving completion status for user %s: %s: %s",
                username,
                e,
                e.exception if hasattr(e, "exception") else "",
            )

        raise GradeError()
