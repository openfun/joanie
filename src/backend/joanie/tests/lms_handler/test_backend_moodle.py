"""Test suite for the Moodle LMS Backend."""
from http import HTTPStatus
from logging import ERROR

from django.test import TestCase
from django.test.utils import override_settings

import responses
from requests import RequestException

from joanie.core import factories, models
from joanie.core.exceptions import EnrollmentError
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.moodle import MoodleLMSBackend

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

MOODLE_RESPONSE_ENROLLMENTS = [
    {
        "id": 2,
        "username": "admin",
        "firstname": "Admin",
        "lastname": "User",
        "fullname": "Admin User",
        "email": "admin@example.com",
        "department": "",
        "firstaccess": 1704715031,
        "lastaccess": 1704717064,
        "lastcourseaccess": 1704716089,
        "description": "",
        "descriptionformat": 1,
        "profileimageurlsmall": (
            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
        ),
        "profileimageurl": "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1",
        "roles": [
            {
                "roleid": 3,
                "name": "",
                "shortname": "editingteacher",
                "sortorder": 0,
            }
        ],
        "enrolledcourses": [{"id": 2, "fullname": "Cours 1", "shortname": "cours 1"}],
    },
    {
        "id": 5,
        "username": "student",
        "firstname": "Student",
        "lastname": "User",
        "fullname": "Student User",
        "email": "student@example.com",
        "department": "",
        "firstaccess": 1704716076,
        "lastaccess": 1704716076,
        "lastcourseaccess": 1704716114,
        "description": "",
        "descriptionformat": 1,
        "profileimageurlsmall": (
            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
        ),
        "profileimageurl": "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1",
        "roles": [{"roleid": 5, "name": "", "shortname": "student", "sortorder": 0}],
        "enrolledcourses": [{"id": 2, "fullname": "Cours 1", "shortname": "cours 1"}],
    },
    {
        "id": 6,
        "username": "manager",
        "firstname": "Manager",
        "lastname": "User",
        "fullname": "Manager User",
        "email": "manager@example.com",
        "department": "",
        "firstaccess": 1704716259,
        "lastaccess": 1704716259,
        "lastcourseaccess": 0,
        "description": "",
        "descriptionformat": 1,
        "profileimageurlsmall": (
            "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
        ),
        "profileimageurl": "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1",
        "roles": [{"roleid": 5, "name": "", "shortname": "student", "sortorder": 0}],
    },
]

MOODLE_RESPONSE_ROLES = [
    {
        "id": 1,
        "name": "",
        "shortname": "manager",
        "description": "",
        "sortorder": 1,
        "archetype": "manager",
    },
    {
        "id": 2,
        "name": "",
        "shortname": "coursecreator",
        "description": "",
        "sortorder": 2,
        "archetype": "coursecreator",
    },
    {
        "id": 3,
        "name": "",
        "shortname": "editingteacher",
        "description": "",
        "sortorder": 3,
        "archetype": "editingteacher",
    },
    {
        "id": 4,
        "name": "",
        "shortname": "teacher",
        "description": "",
        "sortorder": 4,
        "archetype": "teacher",
    },
    {
        "id": 5,
        "name": "",
        "shortname": "student",
        "description": "",
        "sortorder": 5,
        "archetype": "student",
    },
    {
        "id": 6,
        "name": "",
        "shortname": "guest",
        "description": "",
        "sortorder": 6,
        "archetype": "guest",
    },
    {
        "id": 7,
        "name": "",
        "shortname": "user",
        "description": "",
        "sortorder": 7,
        "archetype": "user",
    },
    {
        "id": 8,
        "name": "",
        "shortname": "frontpage",
        "description": "",
        "sortorder": 8,
        "archetype": "frontpage",
    },
]

MOODLE_RESPONSE_USERS = {
    "users": [
        {
            "id": 5,
            "username": "student",
            "firstname": "Student",
            "lastname": "User",
            "fullname": "Student User",
            "email": "student@example.com",
            "department": "",
            "firstaccess": 1704716076,
            "lastaccess": 1704716076,
            "auth": "manual",
            "suspended": False,
            "confirmed": True,
            "lang": "en",
            "theme": "",
            "timezone": "99",
            "mailformat": 1,
            "description": "",
            "descriptionformat": 1,
            "profileimageurlsmall": (
                "https://moodle.test/theme/image.php/boost/core/1704714971/u/f2"
            ),
            "profileimageurl": (
                "https://moodle.test/theme/image.php/boost/core/1704714971/u/f1"
            ),
        }
    ],
    "warnings": [],
}


@override_settings(
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "a_secure_api_token",
            "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
            "BASE_URL": "http://moodle.test/webservice/rest/server.php",
            "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
            "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
        },
        {
            "API_TOKEN": "a_secure_api_token",
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "BASE_URL": "http://openedx.test",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
            "SELECTOR_REGEX": r"^.*/courses/(?P<course_id>.*)/info/?$",
        },
    ]
)
class MoodleLMSBackendTestCase(TestCase):
    """Test suite for the Moodle LMS Backend."""

    maxDiff = None

    def setUp(self):
        """Set up the test suite."""
        self.resource_link = "http://moodle.test/course/view.php?id=2"
        self.backend = LMSHandler.select_lms(self.resource_link)

    def test_backend_moodle_extract_course_id_from_resource_link(self):
        """
        From a resource_link, Moodle backend should be able
        to extract a course_id
        """
        resource_link = "http://moodle.test/course/view.php?id=2"
        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, MoodleLMSBackend)

        course_id = backend.extract_course_id(resource_link)
        self.assertEqual(course_id, 2)

        resource_link = "http://moodle.test/course/view.php?id=2&section=1"
        backend = LMSHandler.select_lms(resource_link)
        self.assertIsInstance(backend, MoodleLMSBackend)

        course_id = backend.extract_course_id(resource_link)
        self.assertEqual(course_id, 2)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_enrollments(self):
        """
        Retrieving course run's enrollments should return enrollments details.
        """

        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            json=MOODLE_RESPONSE_ENROLLMENTS,
            status=200,
        )

        enrollments = self.backend.get_enrollments(self.resource_link)

        assert enrollments == MOODLE_RESPONSE_ENROLLMENTS

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_enrollments_failed(self):
        """
        If retrieving course run's enrollments failed, it should return None.
        """
        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            json={"error": "Something went wrong..."},
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs:
            enrollments = self.backend.get_enrollments(self.resource_link)

        self.assertIsNone(enrollments)
        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving enrollments: Empty response from server!"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_enrollment(self):
        """
        Retrieving an enrollment for a course run should filter enrollments.
        """

        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            json=MOODLE_RESPONSE_ENROLLMENTS,
            status=200,
        )

        enrollment = self.backend.get_enrollment("student", self.resource_link)
        assert enrollment == MOODLE_RESPONSE_ENROLLMENTS[1]

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_enrollment_failed(self):
        """
        If retrieving an enrollment for a course run failed, it should return None.
        """
        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            json={"error": "Something went wrong..."},
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs:
            enrollment = self.backend.get_enrollment("student", self.resource_link)

        self.assertIsNone(enrollment)
        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving enrollments: "
                "Empty response from server!",
                "ERROR:joanie.lms_handler.backends.moodle:"
                "No enrollments found for course run http://moodle.test/course/view.php?id=2",
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_enrollment_user_not_found(self):
        """
        Retrieving an enrollment for a course run should filter enrollments.
        """

        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            json=MOODLE_RESPONSE_ENROLLMENTS,
            status=200,
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs:
            enrollment = self.backend.get_enrollment("unknown", self.resource_link)

        self.assertIsNone(enrollment)
        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "No enrollment found for user unknown "
                "in course run http://moodle.test/course/view.php?id=2",
            ],
        )
