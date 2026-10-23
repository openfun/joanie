"""
Tests for CourseRun web hook, Moodle backend.

Mirrors `test_api_course_run_sync_edx.py`: the Moodle sync workflow must
offer the exact same guarantees as the historical edX one (signature check,
course run creation/update, course grouping across sessions), the only
difference being how the course code is extracted from the sync payload
(edX: from the `resource_link`'s `course-v1` key: Moodle: from the
`idnumber` field, following FUN's unified course key nomenclature
`[course_number]-session[N]M`, e.g. "71015-session01M").
"""

import hashlib
import hmac
import json
from http import HTTPStatus

from django.test import override_settings

from joanie.core.factories import CourseFactory, CourseRunFactory
from joanie.core.models import Course, CourseRun
from joanie.lms_handler.serializers import SyncCourseRunSerializer
from joanie.tests.base import BaseAPITestCase

SHARED_SECRET = "shared secret"


def sign(data):
    """Compute the HMAC-SHA256 signature header Joanie expects for `data`.

    Joanie signs the exact JSON body sent (see `check_signature`), itself
    produced by Django's test client via `json.dumps(data)` when posting
    with `content_type="application/json"`. Computing it here rather than
    hardcoding digests keeps these tests readable and safe to extend.
    """
    body = json.dumps(data)
    digest = hmac.new(
        SHARED_SECRET.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"SIG-HMAC-SHA256 {digest}"


@override_settings(
    JOANIE_COURSE_RUN_SYNC_SECRETS=[SHARED_SECRET],
    JOANIE_LMS_BACKENDS=[
        {
            "API_TOKEN": "a_secure_api_token",
            "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
            "BASE_URL": "http://moodle.test/webservice/rest/server.php",
            "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
            "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
        }
    ],
    TIME_ZONE="UTC",
)
class SyncCourseRunApiMoodleTestCase(BaseAPITestCase):
    """Test calls to sync a Moodle course run via the API endpoint."""

    def test_api_course_run_sync_moodle_missing_signature(self):
        """The course run synchronization API endpoint requires a signature."""
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync", data, content_type="application/json"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json(), {"detail": "Missing authentication."})
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_moodle_invalid_signature(self):
        """The course run synchronization API endpoint requires a valid signature."""
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION="invalid authorization",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Invalid authentication."})
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_moodle_missing_resource_link(self):
        """
        If the data submitted is missing a resource link, it should return a 400 error.
        """
        data = {
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(), {"resource_link": ["This field is required."]}
        )
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_moodle_invalid_field(self):
        """
        If the submitted data is invalid, the course run synchronization view should return
        a 400 error.
        """
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": 1,
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "start": [
                    (
                        "Datetime has wrong format. Use one of these formats instead: "
                        "YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]."
                    )
                ]
            },
        )
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_moodle_missing_idnumber(self):
        """
        If the submitted data is missing `idnumber` and no course run already exists for this
        resource link, it should return a 400 error: an unparseable course code must never
        silently create an orphan Course.
        """
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("idnumber", response.json())
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_moodle_invalid_idnumber_format(self):
        """
        If the submitted `idnumber` does not match FUN's unified course key nomenclature and
        no course run already exists for this resource link, it should return a 400 error.
        """
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            # Historical establishment-prefixed format, no longer valid for Moodle.
            "idnumber": "87_046_session01_m",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertIn("idnumber", response.json())
        self.assertEqual(CourseRun.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_api_course_run_sync_moodle_create_unknown_course_with_title(self):
        """
        If the submitted data is not related to an existing course run and the related course
        can't be found, a new course should be created with the title passed for the course_run.
        """
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
            "title": "my course run",
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course: code is the course number only, establishment-free,
        # session and platform indicator segments stripped.
        course = Course.objects.get()
        self.assertEqual(course.code, "71015")
        self.assertEqual(course.title, "my course run")

        # Check the new course run
        course_run = CourseRun.objects.get(course=course)
        self.assertEqual(course_run.title, "my course run")
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("title")
        data.pop("idnumber")
        self.assertEqual(serializer.data, data)

    def test_api_course_run_sync_moodle_create_unknown_course_no_title(self):
        """
        If the submitted data does not include the "title" field and is not related to an
        existing course run and the related course can't be found, a new course should be
        created with the course code passed in the course_run synchronization data.
        """
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course
        course = Course.objects.get()
        self.assertEqual(course.code, "71015")
        self.assertEqual(course.title, "71015")

        # Check the new course run: no title was submitted, it should fall back to the
        # course's title rather than being left empty in the back office.
        course_run = CourseRun.objects.get(course=course)
        self.assertEqual(course_run.title, "71015")
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("idnumber")
        self.assertEqual(serializer.data, data)

    def test_api_course_run_sync_moodle_create(self):
        """
        If the submitted data is not related to an existing course run, a new course run should
        be created.
        """
        CourseFactory(code="71015")
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
            "title": "my course run",
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course run
        course_run = CourseRun.objects.get()
        self.assertEqual(course_run.title, "my course run")
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("title")
        data.pop("idnumber")
        self.assertEqual(serializer.data, data)

    def test_api_course_run_sync_moodle_create_second_session_same_course(self):
        """
        Two sessions of the same Moodle course (same course number, different session
        segment in `idnumber`) must map to the same `Course`, each sync creating a new
        `CourseRun` rather than a new `Course` -- the same guarantee edX offers today via
        `OpenEdXLMSBackend.extract_course_number` discarding the course run segment.
        """
        data_session_1 = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
            "title": "my course - session 1",
        }
        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data_session_1,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data_session_1),
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        data_session_2 = {
            "resource_link": "http://moodle.test/course/view.php?id=3",
            "idnumber": "71015-session02M",
            "start": "2021-09-09T09:31:59.417817Z",
            "end": "2021-12-14T09:31:59.417895Z",
            "enrollment_start": "2021-08-09T09:31:59.417936Z",
            "enrollment_end": "2021-09-24T09:31:59.417972Z",
            "languages": ["fr"],
            "title": "my course - session 2",
        }
        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data_session_2,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data_session_2),
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)

        # Only one Course should have been created, with two course runs attached,
        # each keeping its own title (not the course's).
        self.assertEqual(Course.objects.count(), 1)
        course = Course.objects.get(code="71015")
        course_runs = CourseRun.objects.filter(course=course).order_by("start")
        self.assertEqual(
            list(course_runs.values_list("translations__title", flat=True)),
            ["my course - session 1", "my course - session 2"],
        )

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_moodle_create_partial_required(self):
        """
        If the submitted data is not related to an existing course run and some required fields
        are missing, it should raise a 400.
        """
        CourseFactory(code="71015")
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "end": "2021-03-14T09:31:59.417895Z",
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.json(), {"languages": ["This field is required."]})
        self.assertEqual(CourseRun.objects.count(), 0)

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_moodle_create_partial_not_required(self):
        """
        If the submitted data is not related to an existing course run and some optional fields
        are missing, it should create the course run.
        """
        CourseFactory(code="71015")
        data = {
            "resource_link": "http://moodle.test/course/view.php?id=2",
            "idnumber": "71015-session01M",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check the new course run
        course_run = CourseRun.objects.get()
        serializer = SyncCourseRunSerializer(instance=course_run)
        data.pop("idnumber")
        data.update({"start": None, "end": None, "enrollment_start": None})
        self.assertEqual(serializer.data, data)

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_moodle_existing_published(self):
        """
        If a course run exists for this resource link, it should be updated. On update,
        `idnumber` is not required anymore since the course is already resolved.
        """
        link = "http://moodle.test/course/view.php?id=2"
        CourseFactory(code="71015")
        CourseRunFactory(resource_link=link)

        data = {
            "resource_link": link,
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check that the existing course run was updated
        course_run = CourseRun.objects.get()
        serializer = SyncCourseRunSerializer(instance=course_run)
        self.assertEqual(serializer.data, data)

    @override_settings(TIME_ZONE="UTC")
    def test_api_course_run_sync_moodle_existing_partial(self):
        """
        If a course run exists for this resource link, it can be partially updated and the other
        fields should not be altered.
        """
        link = "http://moodle.test/course/view.php?id=2"
        course = CourseFactory(code="71015")
        course_run = CourseRunFactory(course=course, resource_link=link)

        origin_data = SyncCourseRunSerializer(instance=course_run).data
        data = {"resource_link": link, "end": "2021-03-14T09:31:59.417895Z"}

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check that the course run was updated
        course_run = CourseRun.objects.get(course=course)
        serializer = SyncCourseRunSerializer(instance=course_run)

        self.assertEqual(serializer.data["end"], data["end"])
        for field in serializer.fields:
            if field == "end":
                continue
            self.assertEqual(serializer.data[field], origin_data[field])

    @override_settings(
        TIME_ZONE="UTC",
        JOANIE_LMS_BACKENDS=[
            {
                "API_TOKEN": "a_secure_api_token",
                "BACKEND": "joanie.lms_handler.backends.moodle.MoodleLMSBackend",
                "BASE_URL": "http://moodle.test/webservice/rest/server.php",
                "COURSE_RUN_SYNC_NO_UPDATE_FIELDS": ["languages", "start"],
                "COURSE_REGEX": r"^.*/course/view.php\?id=.*$",
                "SELECTOR_REGEX": r"^.*/course/view.php\?id=.*$",
            }
        ],
    )
    def test_api_course_run_sync_moodle_with_no_update_fields(self):
        """
        If a course run exists and the LMS Backend has course run protected fields,
        these fields should not be updated.
        """
        link = "http://moodle.test/course/view.php?id=2"
        course = CourseFactory(code="71015")
        course_run = CourseRunFactory(course=course, resource_link=link)

        origin_data = SyncCourseRunSerializer(instance=course_run).data
        data = {
            "resource_link": link,
            "start": "2020-12-09T09:31:59.417817Z",
            "end": "2021-03-14T09:31:59.417895Z",
            "enrollment_start": "2020-11-09T09:31:59.417936Z",
            "enrollment_end": "2020-12-24T09:31:59.417972Z",
            "languages": ["fr"],
        }

        response = self.client.post(
            "/api/v1.0/course-runs-sync",
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=sign(data),
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json(), {"success": True})
        self.assertEqual(CourseRun.objects.count(), 1)

        # Check that the course run was updated except protected fields
        course_run = CourseRun.objects.get(course=course)
        serializer = SyncCourseRunSerializer(instance=course_run)

        no_update_fields = ["languages", "start"]
        for field in serializer.fields:
            if field in no_update_fields:
                self.assertEqual(serializer.data[field], origin_data[field])
            else:
                self.assertEqual(serializer.data[field], data[field])
