"""
Backend to connect Joanie to Moodle LMS
"""

import logging
from typing import Literal
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


class MoodleUserException(Exception):
    """Raised when a user is not found in Moodle."""


class MoodleUserCreateException(Exception):
    """Raised when a user creation fails in Moodle."""


class MoodleUserUpdateException(Exception):
    """Raised when a user update fails in Moodle."""


class MoodleGroupCourseCreateException(Exception):
    """Raised when group course creation fails in Moodle."""


class MoodleAddUserGroupException(Exception):
    """Raised when adding user to group course fails in Moodle."""


class MoodleGetGroupException(Exception):
    """Raised when fetching groups in course fails in Moodle."""


class MoodleLMSBackend(BaseLMSBackend):
    """LMS Backend to connect Joanie to Moodle LMS"""

    name = "moodle"

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

    def extract_course_id(self, resource_link: str):
        """Extract the LMS course id from the course run url."""
        parsed_url = urlparse(resource_link)
        query_parameters = parse_qs(parsed_url.query)
        return int(query_parameters.get("id")[0])

    def get_enrollment(self, username: str, resource_link: str):
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

    def get_enrollments(self, resource_link: str):
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
    def get_user(self, value: str, key: Literal["username", "email"] = "username"):
        """Retrieve user data response through username or email."""
        value = value.lower()
        criteria = {"key": key, "value": value}
        try:
            res = self.moodle("core_user_get_users", criteria=[criteria])
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error("Moodle error while retrieving user %s: %s", value, e)
            raise MoodleUserException() from e
        try:
            # username and email are both unique in Moodle
            return res.get("users", [])[0]
        except IndexError as e:
            logger.info("User %s not found in Moodle", value)
            raise MoodleUserException() from e

    def create_user(self, user):
        """Create a user."""
        user.username = user.username.lower()
        logger.info("username %s", user.username)
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

    def update_user_info(
        self, user_moodle_id: str, username: str, update_username=False
    ):
        """
        Update user `alternatename` and `idnumber` fields.
        We may also update the username to have consistent data with previous
        moodle enrollments that were not made through our Richie platform.
        We know that the email adress is the same because of the SSO, we just
        need to update the username.
        """
        username = username.lower()
        user_data = {
            "id": user_moodle_id,
            "idnumber": username,
            "alternatename": username,
        }
        if update_username:
            user_data["username"] = username
        try:
            return self.moodle("core_user_update_users", users=[user_data])
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error("Moodle error while updating user %s: %s", username, e)
            raise MoodleUserUpdateException() from e

    def get_course_group_id(self, resource_link: str):
        """Get the first group of a course in Moodle LMS"""
        course_id = self.extract_course_id(resource_link)
        try:
            response = self.moodle.post(
                "core_group_get_course_groups", courseid=course_id, options=None
            )
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error(
                "Moodle error while retrieving course group %s: %s", course_id, e
            )
            raise MoodleGetGroupException() from e
        try:
            return response[0].get("id")
        except IndexError:
            return None

    def create_group_in_course(self, resource_link: str, name: str):
        """Create the course's group for certificate when it's the first user to enter"""
        course_id = self.extract_course_id(resource_link)
        group_data = {
            "name": name.capitalize(),
            "courseid": course_id,
            "description": "Group dedicated for certificate students",
            "idnumber": name.lower(),
        }
        try:
            return self.moodle.post(
                "core_group_create_groups", groups=[group_data], options=None
            )[0]["id"]
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error(
                "Moodle error while creating group in course id %s: %s", course_id, e
            )
            raise MoodleGroupCourseCreateException() from e

    def add_user_to_group(self, user_id: str, group_id: int):
        """Add learner to specific group id in course"""
        group_user_data = {
            "userid": user_id,
            "groupid": group_id,
        }
        try:
            self.moodle("core_group_add_group_members", members=[group_user_data])
        except (MoodleException, NetworkMoodleException, EmptyResponseException) as e:
            logger.error(
                "Moodle error while adding user %s to group %s : %s",
                user_id,
                group_id,
                e,
            )
            raise MoodleAddUserGroupException() from e
        return True

    def _get_or_create_user_id(self, enrollment):
        """
        Return the Moodle id of the enrollment's user: find it by username, then by
        email (users first enrolled directly via Moodle), and create it if needed.
        `idnumber` and `alternatename` are filled in when missing.
        """
        user_id = None
        username = enrollment.user.username

        try:
            user = self.get_user(username, key="username")
            user_id = user.get("id")
        except MoodleUserException as e:
            if not enrollment.is_active:
                raise EnrollmentError() from e

        # This new part is to update the user who first enrolled directly via Moodle...
        if user_id is None:
            try:
                user = self.get_user(enrollment.user.email, key="email")
            except MoodleUserException:
                user = None

            if user:
                self.update_user_info(user_moodle_id=user.get("id"), username=username)
                user_id = user.get("id")

        # Make sure `idnumber` and `alternatename` are filled, otherwise update them
        if user:
            if not user.get("idnumber") or not user.get("alternatename"):
                self.update_user_info(user_moodle_id=user_id, username=username)

        if user_id is None:
            try:
                user_created = self.create_user(enrollment.user)
            except MoodleUserCreateException as e:
                raise EnrollmentError() from e
            user_id = user_created.get("id")
        return user_id

    def _add_user_to_group(self, enrollment, user_id, group_name):
        """Add the user to the course's group, creating the group if needed."""
        resource_link = enrollment.course_run.resource_link
        group_id = self.get_course_group_id(resource_link=resource_link)
        if not group_id:
            group_id = self.create_group_in_course(
                resource_link=resource_link, name=group_name
            )
        self.add_user_to_group(user_id=user_id, group_id=group_id)

    # pylint: disable=too-many-branches
    def set_enrollment(self, enrollment):
        """Activate/deactivate an enrollment."""
        user_id = self._get_or_create_user_id(enrollment)
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

    def get_grades(self, username: str, resource_link: str):
        """Get user's grades for a course run given its url."""
        try:
            user_id = self.get_user(username, key="username")["id"]
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
