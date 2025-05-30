"""Tests for the import_enrollments task."""
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from os.path import dirname, join, realpath
from unittest.mock import patch

from django.test import override_settings

from joanie.core import factories, models
from joanie.core.enums import ENROLLMENT_STATE_SET
from joanie.edx_imports import edx_factories
from joanie.edx_imports.tasks.enrollments import import_enrollments
from joanie.edx_imports.utils import extract_course_number, make_date_aware
from joanie.lms_handler.api import detect_lms_from_resource_link
from joanie.tests.base import LoggingTestCase

LOGO_NAME = "creative_common.jpeg"
with open(join(dirname(realpath(__file__)), f"images/{LOGO_NAME}"), "rb") as logo:
    LOGO_CONTENT = logo.read()


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
    },
    JOANIE_LMS_BACKENDS=[
        {
            "BACKEND": "joanie.lms_handler.backends.openedx.OpenEdXLMSBackend",
            "COURSE_REGEX": r"^.*/courses/(?P<course_id>.*)/course/?$",
        }
    ],
    EDX_DATABASE_USER="test",
    EDX_DATABASE_PASSWORD="test",
    EDX_DATABASE_HOST="test",
    EDX_DATABASE_PORT="1234",
    EDX_DATABASE_NAME="test",
    EDX_DOMAIN="openedx.test",
    EDX_TIME_ZONE="UTC",
    TIME_ZONE="UTC",
)
class EdxImportEnrollmentsTestCase(LoggingTestCase):
    """Tests for the import_enrollments task."""

    maxDiff = None

    def tearDown(self):
        """Tear down the test case."""
        edx_factories.session.rollback()

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are created from the edx enrollments.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
            )
            factories.UserFactory.create(username=edx_enrollment.user.username)
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        import_enrollments()

        self.assertEqual(models.Enrollment.objects.count(), len(edx_enrollments))
        for edx_enrollment in edx_enrollments:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(enrollment.user.username, edx_enrollment.user.username)
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )
            self.assertEqual(enrollment.state, ENROLLMENT_STATE_SET)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create_offset_limit(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are created from the edx enrollments.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(100)
        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
            )
            factories.UserFactory.create(username=edx_enrollment.user.username)
        mock_get_enrollments.return_value = edx_enrollments[20:30]
        mock_get_enrollments_count.return_value = 10

        import_enrollments(global_offset=20, import_size=10)

        mock_get_enrollments.assert_called_once_with(20, 1000, course_id=None)

        self.assertEqual(models.Enrollment.objects.count(), 10)
        for edx_enrollment in edx_enrollments[20:30]:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(enrollment.user.username, edx_enrollment.user.username)
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )
            self.assertEqual(enrollment.state, ENROLLMENT_STATE_SET)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    @patch("joanie.core.models.Enrollment.set")
    def test_import_enrollments_update(
        self, _, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are updated from the edx enrollments.
        """
        enrollments = factories.EnrollmentFactory.create_batch(1)
        lms = detect_lms_from_resource_link(enrollments[0].course_run.resource_link)
        edx_enrollments = [
            edx_factories.EdxEnrollmentFactory.create(
                user_id=enrollment.user.id,
                user__username=enrollment.user.username,
                course_id=lms.extract_course_id(enrollment.course_run.resource_link),
            )
            for enrollment in enrollments
        ]
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        import_enrollments()

        self.assertEqual(models.Enrollment.objects.count(), len(edx_enrollments))
        for edx_enrollment in edx_enrollments:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertNotEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create_missing_course_run(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are created from the edx enrollments if the course run
        exists.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        edx_enrollments_with_course_run = []
        i = 0
        for edx_enrollment in edx_enrollments:
            if i % 2 == 0:
                factories.CourseRunFactory.create(
                    course__code=extract_course_number(edx_enrollment.course_id),
                    resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
                )
                edx_enrollments_with_course_run.append(edx_enrollment)
            factories.UserFactory.create(username=edx_enrollment.user.username)
            i += 1
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        import_enrollments()

        self.assertEqual(
            models.CourseRun.objects.count(), len(edx_enrollments_with_course_run)
        )
        self.assertEqual(
            models.Enrollment.objects.count(), len(edx_enrollments_with_course_run)
        )

        for edx_enrollment in edx_enrollments_with_course_run:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(enrollment.user.username, edx_enrollment.user.username)
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create_dry_run(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that no enrollment is created from the edx enrollments in dry run mode.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
            )
            factories.UserFactory.create(username=edx_enrollment.user.username)
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        import_enrollments(dry_run=True)

        self.assertEqual(models.Enrollment.objects.count(), 0)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create_similar_resource_links(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that matching course run is found when resource links are similar.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
            )
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/infos/",
            )
            factories.UserFactory.create(username=edx_enrollment.user.username)
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        import_enrollments()

        self.assertEqual(models.Enrollment.objects.count(), len(edx_enrollments))
        for edx_enrollment in edx_enrollments:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(enrollment.user.username, edx_enrollment.user.username)
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )
            self.assertEqual(enrollment.state, ENROLLMENT_STATE_SET)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create_multiple_resource_links(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that exception is catch with context.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/infos/",
            )
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=(
                    f"http://openedx.test/courses/{edx_enrollment.course_id.upper()}/infos/"
                ),
            )
            factories.UserFactory.create(username=edx_enrollment.user.username)
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        with self.assertLogs("joanie") as logger:
            import_enrollments()

        self.assertEqual(models.Enrollment.objects.count(), 0)

        expected_logs = [
            ("INFO", "10 enrollments to import by batch of 1000"),
        ]

        expected_logs += [
            (
                "ERROR",
                "Error creating Enrollment: "
                "get() returned more than one CourseRun -- it returned 2!",
                {
                    "exception": models.courses.CourseRun.MultipleObjectsReturned,
                    "edx_enrollment": dict,
                },
            ),
        ] * len(edx_enrollments)

        expected_logs += [
            ("INFO", "100% 10/10 : 0 enrollments created, 0 skipped, 10 errors"),
            ("INFO", "1 import enrollments tasks launched"),
        ]
        self.assertLogsEquals(logger.records, expected_logs)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_import_enrollments_create_duplicate_entries(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Trying to insert duplicate enrollments in the same bulk_create should ignore the duplicates.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)

        for edx_enrollment in edx_enrollments:
            factories.CourseRunFactory.create(
                course__code=extract_course_number(edx_enrollment.course_id),
                resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
            )
            factories.UserFactory.create(username=edx_enrollment.user.username)

        edx_enrollments.append(edx_enrollments[0])
        edx_enrollments.append(edx_enrollments[1])
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)
        self.assertEqual(len(edx_enrollments), 12)
        self.assertEqual(models.Enrollment.objects.count(), 0)

        import_enrollments()

        self.assertEqual(models.Enrollment.objects.count(), 10)
        for edx_enrollment in edx_enrollments:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_enrollment.user.username,
                course_run__course__code=extract_course_number(
                    edx_enrollment.course_id
                ),
            )
            self.assertEqual(enrollment.is_active, edx_enrollment.is_active)
            self.assertEqual(
                enrollment.created_on, make_date_aware(edx_enrollment.created)
            )
            self.assertEqual(enrollment.user.username, edx_enrollment.user.username)
            self.assertEqual(
                enrollment.course_run.course.code,
                extract_course_number(edx_enrollment.course_id),
            )
            self.assertEqual(enrollment.state, ENROLLMENT_STATE_SET)
