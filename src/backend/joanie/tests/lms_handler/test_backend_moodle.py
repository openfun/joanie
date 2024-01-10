"""Test suite for the Moodle LMS Backend."""
import random
from http import HTTPStatus
from logging import ERROR

from django.test import TestCase
from django.test.utils import override_settings

import responses
from requests import RequestException

from joanie.core import factories, models
from joanie.core.exceptions import EnrollmentError
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.moodle import (
    MoodleLMSBackend,
    MoodleUserCreateException,
)

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter,too-many-lines,too-many-public-methods

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

    @override_settings(MOODLE_AUTH_METHOD="moodle_auth_method")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_user(self):
        """
        Creating a user should return a dict containing the user's id and username.
        """
        user = factories.UserFactory(
            first_name="John Doe",
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_create_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][username]": user.username,
                        "users[0][firstname]": user.first_name,
                        "users[0][lastname]": user.last_name or ".",
                        "users[0][email]": user.email,
                        "users[0][auth]": "moodle_auth_method",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={"id": 5, "username": user.username},
        )

        result = self.backend.create_user(user)

        self.assertEqual(result, {"id": 5, "username": user.username})

    @override_settings(MOODLE_AUTH_METHOD="moodle_auth_method")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_user_error(self):
        """
        Creating a user should return a dict containing the user's id and username.
        """
        user = factories.UserFactory(
            first_name="John Doe",
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_create_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][username]": user.username,
                        "users[0][firstname]": user.first_name,
                        "users[0][lastname]": user.last_name or ".",
                        "users[0][email]": user.email,
                        "users[0][auth]": "moodle_auth_method",
                    }
                )
            ],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(MoodleUserCreateException):
            self.backend.create_user(user)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                f"Moodle error while creating user {user.username}: "
                f"Empty response from server!"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_enroll(self):
        """
        Updating a user's enrollment to a course run should return a boolean
        corresponding to the success of the operation.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(
            username="student",
        )
        enrollment = models.Enrollment(course_run=course_run, user=user, is_active=True)

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_USERS,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("enrol_manual_enrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": course_id,
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
        )

        result = self.backend.set_enrollment(enrollment)

        self.assertTrue(result)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_unenroll(self):
        """
        Updating a user's enrollment to a course run should return a boolean
        corresponding to the success of the operation.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(
            username="student",
        )
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=False
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_USERS,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("enrol_manual_unenrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": course_id,
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
        )

        result = self.backend.set_enrollment(enrollment)

        self.assertTrue(result)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_user_error(self):
        """
        When un-enrolling, if user is not found, it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        user = factories.UserFactory(
            username="student",
        )
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=False
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(EnrollmentError):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving user student: Empty response from server!"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_user_not_found(self):
        """
        When enrolling, if user is not found, it should be created.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(
            username="student",
            first_name="John Doe",
        )
        enrollment = models.Enrollment(course_run=course_run, user=user, is_active=True)

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "users": [],
                "warnings": [],
            },
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_create_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][username]": user.username,
                        "users[0][firstname]": user.first_name,
                        "users[0][lastname]": user.last_name or ".",
                        "users[0][email]": user.email,
                        "users[0][auth]": "oauth2",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={"id": 5, "username": user.username},
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("enrol_manual_enrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": course_id,
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
        )

        result = self.backend.set_enrollment(enrollment)

        self.assertTrue(result)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_unenroll_user_not_found(self):
        """
        When unenrolling, if user is not found, it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        user = factories.UserFactory(
            username="student",
        )
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=False
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json={
                "users": [],
                "warnings": [],
            },
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(EnrollmentError):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:User student not found in Moodle"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_student_role_error(self):
        """
        When enrolling, if getting roles fails, it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        user = factories.UserFactory(
            username="student",
        )
        is_active = random.choice([True, False])
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=is_active
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(EnrollmentError):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:Empty response from server!",
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving student role: "
                "Student role not found in Moodle",
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_student_role_not_found(self):
        """
        When enrolling, if student role is not found, it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        user = factories.UserFactory(
            username="student",
        )
        is_active = random.choice([True, False])
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=is_active
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=[
                {
                    "id": 1,
                    "name": "",
                    "shortname": "manager",
                    "description": "",
                    "sortorder": 1,
                    "archetype": "manager",
                },
            ],
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(EnrollmentError):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving student role: "
                "Student role not found in Moodle"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_enroll_fail(self):
        """
        When enrolling, if Moodle returns an error, it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(
            username="student",
        )
        enrollment = models.Enrollment(course_run=course_run, user=user, is_active=True)

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_USERS,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("enrol_manual_enrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": course_id,
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            body=RequestException("Something went wrong..."),
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(EnrollmentError):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while enrolling user student "
                f"(userid: 5, roleid 5, courseid {course_id}): "
                "A Network error occurred: Something went wrong..."
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_unenroll_fail(self):
        """
        When un-enrolling, if Moodle returns an error, it should raise an EnrollmentError.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(
            username="student",
        )
        enrollment = models.Enrollment(
            course_run=course_run, user=user, is_active=False
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_get_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "criteria[0][key]": "username",
                        "criteria[0][value]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_USERS,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("local_wsgetroles_get_roles"),
            status=HTTPStatus.OK,
            json=MOODLE_RESPONSE_ROLES,
        )

        responses.add(
            responses.POST,
            self.backend.build_url("enrol_manual_unenrol_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "enrolments[0][courseid]": course_id,
                        "enrolments[0][userid]": "5",
                        "enrolments[0][roleid]": "5",
                    }
                )
            ],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            body=RequestException("Something went wrong..."),
        )

        with self.assertLogs(
            "joanie.lms_handler.backends.moodle", level=ERROR
        ) as error_logs, self.assertRaises(EnrollmentError):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while unenrolling user student "
                f"(userid: 5, roleid 5, courseid {course_id}): "
                "A Network error occurred: Something went wrong..."
            ],
        )
