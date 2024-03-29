"""Tests for the migrate_edx command to import course runs from Open edX."""

from unittest.mock import patch

from django.core.management import call_command

import factory

from joanie.core import factories
from joanie.edx_imports import edx_factories
from joanie.tests.edx_imports.base_test_commands_migrate import (
    MigrateOpenEdxBaseTestCase,
)


class MigrateOpenEdxTestCase(MigrateOpenEdxBaseTestCase):
    """Tests for the migrate_edx command to import course runs from Open edX."""

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_runs_create(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are created from the edx course overviews.
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(10)
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--course-runs")

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "10 course_overviews to import by batch of 1000",
            "10 courses created, 0 skipped, 0 errors",
            "100% 10/10 : 10 course runs created, 0 skipped, 0 errors",
            "1 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_create_unknown_course_with_title(
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--course-runs")

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "1 course_overviews to import by batch of 1000",
            "1 courses created, 0 skipped, 0 errors",
            "100% 1/1 : 1 course runs created, 0 skipped, 0 errors",
            "1 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_create_unknown_course_no_title(
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--course-runs")

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "1 course_overviews to import by batch of 1000",
            "1 courses created, 0 skipped, 0 errors",
            "100% 1/1 : 1 course runs created, 0 skipped, 0 errors",
            "1 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_runs_create_same_course(
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
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--course-runs")

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "10 course_overviews to import by batch of 1000",
            "1 courses created, 0 skipped, 0 errors",
            "100% 10/10 : 10 course runs created, 0 skipped, 0 errors",
            "1 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_runs_create_known_course(
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--course-runs")

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "10 course_overviews to import by batch of 1000",
            "0 courses created, 0 skipped, 0 errors",
            "100% 10/10 : 10 course runs created, 0 skipped, 0 errors",
            "1 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_runs_create_dry_run(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are not created from the edx course overviews if the dry-run
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(10)
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--course-runs", "--dry-run")

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "Dry run: no course run will be imported",
            "10 course_overviews to import by batch of 1000",
            "Dry run: 10 courses created, 0 skipped, 0 errors",
            "Dry run: 100% 10/10 : 10 course runs created, 0 skipped, 0 errors",
            "1 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_course_overviews")
    def test_command_migrate_course_runs_create_dry_run_offset_size(
        self, mock_get_course_overviews, mock_get_course_overviews_count
    ):
        """
        Test that course runs are not created from the edx course overviews if the dry-run
        """
        edx_course_overviews = edx_factories.EdxCourseOverviewFactory.create_batch(80)
        mock_get_course_overviews.return_value = edx_course_overviews
        mock_get_course_overviews_count.return_value = len(edx_course_overviews)

        def get_edx_certificates(*args, **kwargs):
            start = args[0]
            stop = start + args[1]
            return edx_course_overviews[start:stop]

        mock_get_course_overviews.side_effect = get_edx_certificates
        mock_get_course_overviews_count.return_value = 60

        with self.assertLogs() as logger:
            call_command(
                "migrate_edx",
                "--skip-check",
                "--course-runs",
                "--course-runs-offset=20",
                "--course-runs-size=60",
                "--batch-size=30",
                "--dry-run",
            )

        expected = [
            "Importing data from Open edX database...",
            "Importing course runs...",
            "Dry run: no course run will be imported",
            "60 course_overviews to import by batch of 30",
            "Dry run: 30 courses created, 0 skipped, 0 errors",
            "Dry run: 83.333% 50/60 : 30 course runs created, 0 skipped, 0 errors",
            "Dry run: 30 courses created, 0 skipped, 0 errors",
            "Dry run: 100% 80/60 : 30 course runs created, 0 skipped, 0 errors",
            "2 import course runs tasks launched",
        ]
        self.assertLogsContains(logger, expected)
