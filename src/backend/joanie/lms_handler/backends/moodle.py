"""
Backend to connect Joanie to Moodle LMS
"""

import logging
import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings

from moodle import Moodle
from moodle.exception import (
    EmptyResponseException,
    MoodleException,
    NetworkMoodleException,
)
from rest_framework.exceptions import ValidationError

from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.lms_handler.serializers import SyncCourseRunSerializer

from .base import BaseLMSBackend

logger = logging.getLogger(__name__)

# FUN's unified course key nomenclature, shared across OpenEdX, Moodle,
# Joanie and Richie: [course_number]-session[N][M], e.g. "71015-session01M".
# Unlike the historical edX-only format, the establishment code is no longer
# part of this field (it is carried by the Moodle course's category instead).
# The session segment and the Moodle platform indicator ("M") are
# intentionally dropped when deriving the Joanie course code, so that every
# session of the same course maps to the same `Course` (one new `CourseRun`
# per session), matching OpenEdXLMSBackend.extract_course_number's behavior
# on the course-v1 key.
MOODLE_COURSE_NUMBER_REGEX = r"^(?P<course_number>\d+)-session\d+M$"


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
        self.role_id = settings.JOANIE_LMS_MOODLE_STUDENT_ROLE_ID

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
            "idnumber": user.username,
            "alternatename": user.username,
        }
        try:
            return self.moodle("core_user_create_users", users=[user_data])[0]
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error("Moodle error while creating user %s: %s", user.username, e)
            raise MoodleUserCreateException() from e

    # pylint: disable=too-many-branches
    def set_enrollment(self, enrollment):
        """Activate/deactivate an enrollment."""
        user_id = None
        try:
            user_id = self.get_user_id(enrollment.user.username)
        except MoodleUserException as e:
            if not enrollment.is_active:
                raise EnrollmentError() from e

        if user_id is None:
            try:
                user_created = self.create_user(enrollment.user)
            except MoodleUserCreateException as e:
                raise EnrollmentError() from e
            user_id = user_created.get("id")

        course_id = self.extract_course_id(enrollment.course_run.resource_link)
        moodle_enrollment = {
            "courseid": course_id,
            "userid": user_id,
            "roleid": self.role_id,
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
                self.role_id,
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
            # moodlepy cast boolean values returned by Moodle web services as int so we have
            # to recast `completed` as a boolean value...
            # (Until moodlepy there is a fix in moddlepy)
            return {"passed": bool(completion.completionstatus.completed)}

        except (MoodleException, EmptyResponseException, NetworkMoodleException) as e:
            logger.error(
                "Moodle error while retrieving completion status for user %s: %s: %s",
                username,
                e,
                e.exception if hasattr(e, "exception") else "",
            )

        raise GradeError()

    def extract_course_number(self, data):
        """Extract the LMS course number from data dictionary.

        Moodle's `idnumber` is expected to follow FUN's unified course key
        nomenclature. We reject the sync outright if it doesn't match: a
        malformed idnumber would otherwise silently create an orphan Course
        or split a course's sessions across several Courses.
        """
        idnumber = data.get("idnumber") or ""
        regex = self.configuration.get(
            "COURSE_NUMBER_REGEX", MOODLE_COURSE_NUMBER_REGEX
        )
        match = re.match(regex, idnumber)
        if not match:
            raise ValidationError(
                {
                    "idnumber": [
                        f"idnumber {idnumber!r} does not match the expected "
                        "course key format (coursenumber-sessionNM)."
                    ]
                }
            )
        return match.group("course_number")

    def clean_course_run_data(self, data):
        """Remove course run's protected fields from the data dictionary."""
        return {
            key: value
            for (key, value) in data.items()
            if key not in self.configuration.get("COURSE_RUN_SYNC_NO_UPDATE_FIELDS", [])
        }

    @staticmethod
    def get_course_run_serializer(data, partial=False):
        """Prepare data and return a bound serializer."""
        return SyncCourseRunSerializer(data=data, partial=partial)
