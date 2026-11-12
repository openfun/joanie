"""Test suite for the Moodle LMS Backend."""

import copy
from http import HTTPStatus
from logging import ERROR, INFO

from django.test import TestCase
from django.test.utils import override_settings

import responses
from requests import RequestException

from joanie.core import factories, models
from joanie.core.exceptions import EnrollmentError, GradeError
from joanie.lms_handler import LMSHandler
from joanie.lms_handler.backends.moodle import (
    MoodleAddUserGroupException,
    MoodleGetGroupException,
    MoodleGroupCourseCreateException,
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
            "idnumber": "student",
            "alternatename": "student",
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
    def test_backend_moodle_get_enrollments_network_exception(self):
        """
        If there is a network exception while retrieving course run's enrollments,
        it should return None.
        """
        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            body=RequestException(),
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
                "Moodle error while retrieving enrollments: A Network error occurred"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_enrollments_moodle_error(self):
        """
        If Moodle returns an error in the body while retrieving course run's enrollments,
        it should return None.
        """
        responses.add(
            responses.POST,
            self.backend.build_url("core_enrol_get_enrolled_users"),
            match=[responses.matchers.urlencoded_params_matcher({"courseid": "2"})],
            json={
                "exception": "Yes Moodle is able to return a 200 while there is an error."
            },
            status=200,
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
                "Moodle error while retrieving enrollments: Error Code: \n"
                "Exception: Yes Moodle is able to return a 200 while there is an error.\n"
                "Message: \nDebug Info: "
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
                        "users[0][idnumber]": user.username,
                        "users[0][alternatename]": user.username,
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=[{"id": 5, "username": user.username}],
        )

        result = self.backend.create_user(user)

        self.assertEqual(result, {"id": 5, "username": user.username})

    @override_settings(MOODLE_AUTH_METHOD="moodle_auth_method")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_user_username_uppercase(self):
        """
        Creating a user with a username with uppercase should work by sending to moodle
        a username in lowercase
        """
        user = factories.UserFactory(first_name="John Doe", username="JohnDoe")

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_create_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][username]": "johndoe",
                        "users[0][firstname]": user.first_name,
                        "users[0][lastname]": user.last_name or ".",
                        "users[0][email]": user.email,
                        "users[0][auth]": "moodle_auth_method",
                        "users[0][idnumber]": "johndoe",
                        "users[0][alternatename]": "johndoe",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=[{"id": 5, "username": "johndoe"}],
        )

        result = self.backend.create_user(user)

        self.assertEqual(result, {"id": 5, "username": user.username})

    @override_settings(MOODLE_AUTH_METHOD="moodle_auth_method")
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_user_error(self):
        """
        An error when creating a user should raise a MoodleUserCreateException.
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
                        "users[0][idnumber]": user.username,
                        "users[0][alternatename]": user.username,
                    }
                )
            ],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(MoodleUserCreateException),
        ):
            self.backend.create_user(user)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                f"Moodle error while creating user {user.username}: "
                "Empty response from server!"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_user_network_error(self):
        """
        If there is a network error while creating a user, it should raise a
        MoodleUserCreateException.
        """
        user = factories.UserFactory(
            first_name="John Doe",
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_create_users"),
            body=RequestException(),
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(MoodleUserCreateException),
        ):
            self.backend.create_user(user)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                f"Moodle error while creating user {user.username}: "
                "A Network error occurred"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_user_moodle_error(self):
        """
        If there is a network error while creating a user, it should raise a
        MoodleUserCreateException.
        """
        user = factories.UserFactory(
            first_name="John Doe",
        )

        responses.add(
            responses.POST,
            self.backend.build_url("core_user_create_users"),
            json={
                "exception": "Yes Moodle is able to return a 200 while there is an error."
            },
            status=200,
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(MoodleUserCreateException),
        ):
            self.backend.create_user(user)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                f"Moodle error while creating user {user.username}: "
                "Error Code: \n"
                "Exception: Yes Moodle is able to return a 200 while there is an error.\n"
                "Message: \nDebug Info: "
            ],
        )

    def _moodle_user_missing_fields(self):
        """Moodle `get_users` response for a user without alternatename/idnumber."""
        # Work on a copy so the module-level constant isn't modified for other tests
        response = copy.deepcopy(MOODLE_RESPONSE_USERS)
        # ASSUMPTION: the user is the first item of a "users" list
        del response["users"][0]["alternatename"]
        response["users"][0]["idnumber"] = ""
        return response

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_update_user_info(self):
        """
        `update_user_info` should send the user's id with `idnumber` and
        `alternatename` set to the lowercased username.
        """
        responses.add(
            responses.POST,
            self.backend.build_url("core_user_update_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][id]": "5",
                        "users[0][idnumber]": "student",
                        "users[0][alternatename]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            body="null",
        )

        # Uppercase username to check it is lowercased in the request
        self.backend.update_user_info("5", "StUdEnT")

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_update_user_info_error(self):
        """
        If Moodle returns an error, `update_user_info` should log it and raise
        a `MoodleUserCreateException`.
        """
        responses.add(
            responses.POST,
            self.backend.build_url("core_user_update_users"),
            status=HTTPStatus.OK,
            json={
                "exception": "moodle_exception",
                "errorcode": "invaliduser",
                "message": "Invalid user",
            },
        )

        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(MoodleUserCreateException):
                self.backend.update_user_info("5", "student")

        self.assertIn("Moodle error while updating user student", logs.output[0])

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_update_user_missing_alternatename_and_idnumber(self):
        """
        Updating a user's enrollment to a course should check if the user's data has
        alternatename and idnumber, otherwise, it should update those fields.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(username="student")
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
            json=self._moodle_user_missing_fields(),
        )

        # The missing fields must trigger a user update
        responses.add(
            responses.POST,
            self.backend.build_url("core_user_update_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][id]": "5",
                        "users[0][idnumber]": "student",
                        "users[0][alternatename]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            body="null",
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
    def test_backend_moodle_get_course_group_id(self):
        """
        `get_course_group_id` should return the id of the first group
        of the course.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]

        responses.add(
            responses.POST,
            self.backend.build_url("core_group_get_course_groups"),
            match=[
                responses.matchers.urlencoded_params_matcher({"courseid": course_id})
            ],
            status=HTTPStatus.OK,
            json=[
                {"id": 7, "courseid": int(course_id), "name": "Group A"},
                {"id": 8, "courseid": int(course_id), "name": "Group B"},
            ],
        )

        group_id = self.backend.get_course_group_id(course_run.resource_link)

        self.assertEqual(group_id, 7)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_course_group_id_error(self):
        """
        If Moodle returns an error, `get_course_group_id` should log it and
        raise a `MoodleGetGroupException`.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]

        responses.add(
            responses.POST,
            self.backend.build_url("core_group_get_course_groups"),
            status=HTTPStatus.OK,
            json={
                "exception": "moodle_exception",
                "errorcode": "invalidcourseid",
                "message": "Invalid course id",
            },
        )

        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(MoodleGetGroupException):
                self.backend.get_course_group_id(course_run.resource_link)

        self.assertIn(
            f"Moodle error while retrieving course group {course_id}",
            logs.output[0],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_group_in_course(self):
        """
        `create_group_in_course` should create a group with a capitalized name
        and a lowercased idnumber, and return the id of the created group.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]

        responses.add(
            responses.POST,
            self.backend.build_url("core_group_create_groups"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "groups[0][name]": "Certificate",
                        "groups[0][courseid]": course_id,
                        "groups[0][description]": (
                            "Group dedicated for certificate students"
                        ),
                        "groups[0][idnumber]": "certificate",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=[
                {
                    "id": 12,
                    "courseid": int(course_id),
                    "name": "Certificate",
                    "idnumber": "certificate",
                }
            ],
        )

        # Mixed case name to check it is capitalized / lowercased in the request
        group_id = self.backend.create_group_in_course(
            course_run.resource_link, "cErTiFiCaTe"
        )

        self.assertEqual(group_id, 12)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_create_group_in_course_error(self):
        """
        If Moodle returns an error, `create_group_in_course` should log it and
        raise a `MoodleGroupCourseCreateException`.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]

        responses.add(
            responses.POST,
            self.backend.build_url("core_group_create_groups"),
            status=HTTPStatus.OK,
            json={
                "exception": "moodle_exception",
                "errorcode": "invalidcourseid",
                "message": "Invalid course id",
            },
        )

        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(MoodleGroupCourseCreateException):
                self.backend.create_group_in_course(
                    course_run.resource_link, "certificate"
                )

        self.assertIn(
            f"Moodle error while creating group in course id {course_id}",
            logs.output[0],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_add_user_to_group(self):
        """
        `add_user_to_group` should look up the user by username, then add them
        to the group and return True.
        """
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
            self.backend.build_url("core_group_add_group_members"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "members[0][userid]": "5",
                        "members[0][groupid]": "12",
                    }
                )
            ],
            status=HTTPStatus.OK,
            body="null",
        )

        result = self.backend.add_user_to_group("student", 12)

        self.assertTrue(result)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_add_user_to_group_error(self):
        """
        If Moodle returns an error while adding the user to the group,
        `add_user_to_group` should log it and raise a `MoodleAddUserGroupException`.
        """
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
            self.backend.build_url("core_group_add_group_members"),
            status=HTTPStatus.OK,
            json={
                "exception": "moodle_exception",
                "errorcode": "cannotaddmember",
                "message": "Cannot add member to group",
            },
        )

        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(MoodleAddUserGroupException):
                self.backend.add_user_to_group("student", 12)

        self.assertIn(
            "Moodle error while adding user student to group 12",
            logs.output[0],
        )

    def _add_update_and_enrol_mocks(self, course_id):
        """Register the mocks for get_users -> update_users -> enrol_users."""
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
            json=self._moodle_user_missing_fields(),
        )
        responses.add(
            responses.POST,
            self.backend.build_url("core_user_update_users"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "users[0][id]": "5",
                        "users[0][idnumber]": "student",
                        "users[0][alternatename]": "student",
                    }
                )
            ],
            status=HTTPStatus.OK,
            body="null",
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

    def _add_create_group_mock(self, course_id, error=False):
        """Register the mock for core_group_create_groups (success or error)."""
        kwargs = {
            "match": [
                responses.matchers.urlencoded_params_matcher(
                    {
                        "groups[0][name]": "Certificate",
                        "groups[0][courseid]": course_id,
                        "groups[0][description]": (
                            "Group dedicated for certificate students"
                        ),
                        "groups[0][idnumber]": "certificate",
                    }
                )
            ]
        }
        if error:
            kwargs = {}
        responses.add(
            responses.POST,
            self.backend.build_url("core_group_create_groups"),
            status=HTTPStatus.OK,
            json=(
                {
                    "exception": "moodle_exception",
                    "errorcode": "invalidcourseid",
                    "message": "Invalid course id",
                }
                if error
                else [{"id": 12, "courseid": int(course_id), "name": "Certificate"}]
            ),
            **kwargs,
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_existing_user_update_enrol_group_success(self):
        """
        An existing user missing `alternatename` and `idnumber` is updated and
        enrolled, then the certificate group is created and the user added to it.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(username="student")
        enrollment = models.Enrollment(course_run=course_run, user=user, is_active=True)

        self._add_update_and_enrol_mocks(course_id)
        self._add_create_group_mock(course_id)
        responses.add(
            responses.POST,
            self.backend.build_url("core_group_add_group_members"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "members[0][userid]": "5",
                        "members[0][groupid]": "12",
                    }
                )
            ],
            status=HTTPStatus.OK,
            body="null",
        )

        self.assertTrue(self.backend.set_enrollment(enrollment))
        group_id = self.backend.create_group_in_course(
            course_run.resource_link, "certificate"
        )
        self.assertEqual(group_id, 12)
        self.assertTrue(self.backend.add_user_to_group("student", group_id))

        # get_users, update_users, enrol_users, create_groups,
        # get_users (inside add_user_to_group), add_group_members
        self.assertEqual(
            [
                call.request.url.split("wsfunction=")[-1].split("&")[0]
                for call in responses.calls
            ],
            [
                "core_user_get_users",
                "core_user_update_users",
                "enrol_manual_enrol_users",
                "core_group_create_groups",
                "core_user_get_users",
                "core_group_add_group_members",
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_existing_user_update_enrol_create_group_fails(self):
        """
        The user is updated and enrolled, but creating the group fails: the error
        is logged, `MoodleGroupCourseCreateException` is raised and the user is
        never added to a group.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(username="student")
        enrollment = models.Enrollment(course_run=course_run, user=user, is_active=True)

        self._add_update_and_enrol_mocks(course_id)
        self._add_create_group_mock(course_id, error=True)

        self.assertTrue(self.backend.set_enrollment(enrollment))

        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(MoodleGroupCourseCreateException):
                self.backend.create_group_in_course(
                    course_run.resource_link, "certificate"
                )

        self.assertIn(
            f"Moodle error while creating group in course id {course_id}",
            logs.output[0],
        )
        # get_users, update_users, enrol_users, create_groups: nothing after
        self.assertEqual(len(responses.calls), 4)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_existing_user_update_enrol_add_to_group_fails(self):
        """
        The user is updated and enrolled and the group is created, but adding the
        user to the group fails: the error is logged and
        `MoodleAddUserGroupException` is raised.
        """
        course_run = factories.CourseRunMoodleFactory(
            is_listed=True,
            state=models.CourseState.ONGOING_OPEN,
        )
        course_id = course_run.resource_link.split("=")[-1]
        user = factories.UserFactory(username="student")
        enrollment = models.Enrollment(course_run=course_run, user=user, is_active=True)

        self._add_update_and_enrol_mocks(course_id)
        self._add_create_group_mock(course_id)
        responses.add(
            responses.POST,
            self.backend.build_url("core_group_add_group_members"),
            status=HTTPStatus.OK,
            json={
                "exception": "moodle_exception",
                "errorcode": "cannotaddmember",
                "message": "Cannot add member to group",
            },
        )

        self.assertTrue(self.backend.set_enrollment(enrollment))
        group_id = self.backend.create_group_in_course(
            course_run.resource_link, "certificate"
        )
        self.assertEqual(group_id, 12)

        with self.assertLogs(level="ERROR") as logs:
            with self.assertRaises(MoodleAddUserGroupException):
                self.backend.add_user_to_group("student", group_id)

        self.assertIn(
            "Moodle error while adding user student to group 12", logs.output[0]
        )
        self.assertEqual(len(responses.calls), 6)

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

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
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
                        "users[0][idnumber]": user.username,
                        "users[0][alternatename]": user.username,
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=[{"id": 5, "username": user.username}],
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

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=INFO
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "INFO:joanie.lms_handler.backends.moodle:User student not found in Moodle"
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

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
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

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
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

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_enroll_network_error(self):
        """
        When enrolling, if there is a network error, it should raise an EnrollmentError.
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
            self.backend.build_url("enrol_manual_enrol_users"),
            body=RequestException(),
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while enrolling user student "
                f"(userid: 5, roleid 5, courseid {course_id}): "
                "A Network error occurred: "
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_unenroll_network_error(self):
        """
        When unenrolling, if there is a network error, it should raise an EnrollmentError.
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
            self.backend.build_url("enrol_manual_unenrol_users"),
            body=RequestException(),
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while unenrolling user student "
                f"(userid: 5, roleid 5, courseid {course_id}): "
                "A Network error occurred: "
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_enroll_moodle_error(self):
        """
        When enrolling, if there is a moodle error, it should raise an EnrollmentError.
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
            self.backend.build_url("enrol_manual_enrol_users"),
            json={
                "exception": "Yes Moodle is able to return a 200 while there is an error."
            },
            status=200,
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while enrolling user student "
                f"(userid: 5, roleid 5, courseid {course_id}): Error Code: \n"
                "Exception: Yes Moodle is able to return a 200 while there is an error.\n"
                "Message: \n"
                "Debug Info: : Yes Moodle is able to return a 200 while there is an error."
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_set_enrollment_unenroll_moodle_error(self):
        """
        When unenrolling, if there is a moodle error, it should raise an EnrollmentError.
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
            self.backend.build_url("enrol_manual_unenrol_users"),
            json={
                "exception": "Yes Moodle is able to return a 200 while there is an error."
            },
            status=200,
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(EnrollmentError),
        ):
            self.backend.set_enrollment(enrollment)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while unenrolling user student "
                f"(userid: 5, roleid 5, courseid {course_id}): Error Code: \n"
                "Exception: Yes Moodle is able to return a 200 while there is an error.\n"
                "Message: \n"
                "Debug Info: : Yes Moodle is able to return a 200 while there is an error."
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_grades(self):
        """
        When get user's grades for a course run, it should return grade details without
        any data transformation
        """
        resource_link = "http://moodle.test/course/view.php?id=2"
        json_response = {
            "completionstatus": {
                "completed": True,
                "aggregation": 1,
                "completions": [
                    {
                        "type": 4,
                        "title": "Activity completion",
                        "status": "Yes",
                        "complete": True,
                        "timecompleted": 1705067787,
                        "details": {
                            "type": "Activity completion",
                            "criteria": (
                                '<a href="https://moodle.test/mod/quiz/view.php?id=3">Quizz 1</a>'
                            ),
                            "requirement": "Marking yourself complete",
                            "status": "",
                        },
                    },
                    {
                        "type": 4,
                        "title": "Activity completion",
                        "status": "Yes",
                        "complete": True,
                        "timecompleted": 1705067739,
                        "details": {
                            "type": "Activity completion",
                            "criteria": (
                                '<a href="https://moodle.test/mod/quiz/view.php?id=4">Quizz 2</a>'
                            ),
                            "requirement": "Marking yourself complete",
                            "status": "",
                        },
                    },
                ],
            },
            "warnings": [],
        }

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
            self.backend.build_url("core_completion_get_course_completion_status"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "courseid": "2",
                        "userid": "5",
                    }
                )
            ],
            status=HTTPStatus.OK,
            json=json_response,
        )

        grades = self.backend.get_grades("student", resource_link)

        self.assertEqual(grades, {"passed": True})

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_grades_user_error(self):
        """
        When get user's grades for a course run, it should return grade details without
        any data transformation
        """
        resource_link = "http://moodle.test/course/view.php?id=2"

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

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(GradeError),
        ):
            self.backend.get_grades("student", resource_link)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving user student: Empty response from server!"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_grades_user_not_found(self):
        """
        When get user's grades for a course run, it should return grade details without
        any data transformation
        """
        resource_link = "http://moodle.test/course/view.php?id=2"

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

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=INFO
            ) as error_logs,
            self.assertRaises(GradeError),
        ):
            self.backend.get_grades("student", resource_link)

        self.assertEqual(
            error_logs.output,
            [
                "INFO:joanie.lms_handler.backends.moodle:User student not found in Moodle"
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_grades_fail(self):
        """
        When get user's grades for a course run, it should return grade details without
        any data transformation
        """
        resource_link = "http://moodle.test/course/view.php?id=2"

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
            self.backend.build_url("core_completion_get_course_completion_status"),
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "courseid": "2",
                        "userid": "5",
                    }
                )
            ],
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            body=RequestException("Something went wrong..."),
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(GradeError),
        ):
            self.backend.get_grades("student", resource_link)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving completion status for user student: "
                "A Network error occurred: Something went wrong..."
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_grades_network_error(self):
        """
        if there is a network error while getting grades, it should raise a GradeError.
        """
        resource_link = "http://moodle.test/course/view.php?id=2"

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
            self.backend.build_url("core_completion_get_course_completion_status"),
            body=RequestException(),
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(GradeError),
        ):
            self.backend.get_grades("student", resource_link)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving completion status for user student: "
                "A Network error occurred: "
            ],
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_moodle_get_grades_moodle_error(self):
        """
        if there is a moodle error while getting grades, it should raise a GradeError.
        """
        resource_link = "http://moodle.test/course/view.php?id=2"

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
            self.backend.build_url("core_completion_get_course_completion_status"),
            json={
                "exception": "Yes Moodle is able to return a 200 while there is an error."
            },
            status=200,
        )

        with (
            self.assertLogs(
                "joanie.lms_handler.backends.moodle", level=ERROR
            ) as error_logs,
            self.assertRaises(GradeError),
        ):
            self.backend.get_grades("student", resource_link)

        self.assertEqual(
            error_logs.output,
            [
                "ERROR:joanie.lms_handler.backends.moodle:"
                "Moodle error while retrieving completion status for user student: "
                "Error Code: \n"
                "Exception: Yes Moodle is able to return a 200 while there is an error.\n"
                "Message: \n"
                "Debug Info: : Yes Moodle is able to return a 200 while there is an error."
            ],
        )
