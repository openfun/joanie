"""Tests for the import_course_runs task."""
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings

import factory

from joanie.core import factories, models
from joanie.edx_imports import edx_factories
from joanie.edx_imports.tasks.course_runs import import_course_runs
from joanie.edx_imports.utils import (
    check_language_code,
    extract_course_number,
    make_date_aware,
)

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
class EdxImportCourseRunsTestCase(TestCase):
    """Tests for the import_course_runs task."""

    maxDiff = None

    def tearDown(self):
        """Tear down the test case."""
        edx_factories.session.rollback()

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_import_course_runs_create(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are created from the edx course overviews.
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(10)
        organizations = {}
        for edx_course_overview in edx_course_overviews:
            edx_relation = edx_factories.EdxCourseUniversityRelationFactory.create(
                course=edx_course_overview.course
            )
            organization = factories.OrganizationFactory.create(
                code=edx_relation.university.code,
            )
            organizations[organization.code] = organization

        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        import_course_runs()

        self.assertEqual(models.Course.objects.count(), len(edx_course_overviews))
        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_overview in edx_course_overviews:
            course = models.Course.objects.get(
                code=extract_course_number(edx_course_overview.id)
            )
            self.assertEqual(course.title, edx_course_overview.display_name)
            self.assertEqual(
                course.created_on, make_date_aware(edx_course_overview.created)
            )
            self.assertEqual(course.organizations.count(), 1)
            self.assertEqual(
                course.organizations.first(),
                organizations[course.organizations.first().code],
            )
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language(edx_course_overview.course.language)
            self.assertEqual(
                course_run.resource_link,
                f"https://{settings.EDX_DOMAIN}/courses/{edx_course_overview.id}/info",
            )
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(
                course_run.languages,
                [check_language_code(edx_course_overview.course.language)],
            )
            self.assertTrue(course_run.is_listed)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_import_course_create_unknown_course_with_title(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are created from the edx course overviews and that the
        course is created if it does not exist.
        """
        edx_course_overviews = [
            edx_factories.EdxCourseOverviewFactory.create(
                id="course-v1:edX+DemoX+01",
                display_name="my course run",
            )
        ]
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        import_course_runs()

        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_overview in edx_course_overviews:
            course = models.Course.objects.get(
                code=extract_course_number(edx_course_overview.id)
            )
            self.assertEqual(course.title, edx_course_overview.display_name)
            self.assertEqual(
                course.created_on, make_date_aware(edx_course_overview.created)
            )
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language(edx_course_overview.course.language)
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(
                course_run.languages,
                [check_language_code(edx_course_overview.course.language)],
            )
            self.assertTrue(course_run.is_listed)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_import_course_create_unknown_course_no_title(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are created from the edx course overviews and that the
        course is created if it does not exist.
        When the course overview has no title, the course title is set to the course
        code.
        """
        edx_course_overviews = [
            edx_factories.EdxCourseOverviewFactory.create(
                id="course-v1:edX+DemoX+01",
                display_name=None,
            )
        ]
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        import_course_runs()

        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        for edx_course_overview in edx_course_overviews:
            course = models.Course.objects.get(
                code=extract_course_number(edx_course_overview.id)
            )
            self.assertEqual(course.title, course.code)
            self.assertEqual(
                course.created_on, make_date_aware(edx_course_overview.created)
            )
            course_run = models.CourseRun.objects.get(
                course=course,
            )
            course_run.set_current_language(edx_course_overview.course.language)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(
                course_run.languages,
                [check_language_code(edx_course_overview.course.language)],
            )
            self.assertTrue(course_run.is_listed)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_import_course_runs_create_same_course(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are created from the edx course overviews and that the
        course is created if it does not exist.
        According to the edx course overview id, only one course is created.
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(
            10, id=factory.Sequence(lambda n: f"course-v1:edX+DemoX+{n}")
        )
        organizations = {}
        for edx_course_overview in edx_course_overviews:
            edx_relation = edx_factories.EdxCourseUniversityRelationFactory.create(
                course=edx_course_overview.course
            )
            organization = factories.OrganizationFactory.create(
                code=edx_relation.university.code,
            )
            organizations[organization.code] = organization
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        import_course_runs()

        self.assertEqual(models.Course.objects.count(), 1)
        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        course = models.Course.objects.get()
        self.assertEqual(course.title, edx_course_overviews[0].display_name)
        self.assertEqual(
            course.created_on, make_date_aware(edx_course_overviews[0].created)
        )
        self.assertEqual(course.organizations.count(), 1)
        self.assertEqual(
            course.organizations.first(),
            organizations[course.organizations.first().code],
        )

        course_runs = models.CourseRun.objects.filter(course=course).order_by(
            "updated_on"
        )
        for edx_course_overview, course_run in zip(
            edx_course_overviews, course_runs, strict=False
        ):
            course_run.set_current_language(edx_course_overview.course.language)
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(
                course_run.languages,
                [check_language_code(edx_course_overview.course.language)],
            )
            self.assertTrue(course_run.is_listed)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_import_course_runs_create_known_course(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are created from the edx course overviews and that the
        course is not updated as it already exists.
        """
        course = factories.CourseFactory(code="DemoX")
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(
            10, id=factory.Sequence(lambda n: f"course-v1:edX+{course.code}+{n}")
        )
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        import_course_runs()

        self.assertEqual(models.Course.objects.count(), 1)
        self.assertEqual(models.CourseRun.objects.count(), len(edx_course_overviews))
        course = models.Course.objects.get()
        self.assertNotEqual(course.title, edx_course_overviews[0].display_name)
        self.assertNotEqual(
            course.created_on, make_date_aware(edx_course_overviews[0].created)
        )

        course_runs = models.CourseRun.objects.filter(course=course).order_by(
            "updated_on"
        )
        for edx_course_overview, course_run in zip(
            edx_course_overviews, course_runs, strict=False
        ):
            course_run.set_current_language(edx_course_overview.course.language)
            self.assertEqual(course_run.title, edx_course_overview.display_name)
            self.assertEqual(
                course_run.start, make_date_aware(edx_course_overview.start)
            )
            self.assertEqual(course_run.end, make_date_aware(edx_course_overview.end))
            self.assertEqual(
                course_run.enrollment_start,
                make_date_aware(edx_course_overview.enrollment_start),
            )
            self.assertEqual(
                course_run.enrollment_end,
                make_date_aware(edx_course_overview.enrollment_end),
            )
            self.assertEqual(
                course_run.languages,
                [check_language_code(edx_course_overview.course.language)],
            )
            self.assertTrue(course_run.is_listed)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_import_course_runs_create_dry_run(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that no course run is created from the edx course overviews in dry run mode.
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(10)
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        import_course_runs(dry_run=True)

        self.assertEqual(models.Course.objects.count(), 0)
        self.assertEqual(models.CourseRun.objects.count(), 0)
