"""Tests for the migrate_edx command to import enrollments from Open edX."""
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from unittest.mock import patch

from django.core.management import call_command

from joanie.core import factories
from joanie.edx_imports import edx_factories
from joanie.edx_imports.utils import extract_course_number
from joanie.lms_handler.api import detect_lms_from_resource_link
from joanie.tests.edx_imports.base_test_commands_migrate import (
    MigrateOpenEdxBaseTestCase,
)


class MigrateOpenEdxTestCase(MigrateOpenEdxBaseTestCase):
    """Tests for the migrate_edx command to import enrollments from Open edX."""

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_command_migrate_enrollments_create(
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--enrollments")

        expected = [
            "Importing data from Open edX database...",
            "Importing enrollments...",
            "10 enrollments to import by batch of 1000",
            "Starting Celery task, importing enrollments...",
            "10 enrollments created, 0 updated, 0 errors",
            "Done executing Celery importing enrollments task...",
            "1 import enrollments tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_command_migrate_enrollments_update(
        self, mock_get_enrollments, mock_get_enrollments_count
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--enrollments")

        expected = [
            "Importing data from Open edX database...",
            "Importing enrollments...",
            "1 enrollments to import by batch of 1000",
            "Starting Celery task, importing enrollments...",
            "0 enrollments created, 1 updated, 0 errors",
            "Done executing Celery importing enrollments task...",
            "1 import enrollments tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_command_migrate_enrollments_create_missing_course_run(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are created from the edx enrollments if the course run
        exists.
        """
        edx_enrollments = edx_factories.EdxEnrollmentFactory.create_batch(10)
        edx_enrollments_with_course_run = []
        edx_enrollments_without_course_run = []
        i = 0
        for edx_enrollment in edx_enrollments:
            if i % 2 == 0:
                factories.CourseRunFactory.create(
                    course__code=extract_course_number(edx_enrollment.course_id),
                    resource_link=f"http://openedx.test/courses/{edx_enrollment.course_id}/course/",
                )
                edx_enrollments_with_course_run.append(edx_enrollment)
            else:
                edx_enrollments_without_course_run.append(edx_enrollment)
            factories.UserFactory.create(username=edx_enrollment.user.username)
            i += 1
        mock_get_enrollments.return_value = edx_enrollments
        mock_get_enrollments_count.return_value = len(edx_enrollments)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--enrollments")

        expected = [
            "Importing data from Open edX database...",
            "Importing enrollments...",
            "10 enrollments to import by batch of 1000",
            "Starting Celery task, importing enrollments...",
            f"No CourseRun found for {edx_enrollments_without_course_run[0].course_id}",
            f"No CourseRun found for {edx_enrollments_without_course_run[1].course_id}",
            f"No CourseRun found for {edx_enrollments_without_course_run[2].course_id}",
            f"No CourseRun found for {edx_enrollments_without_course_run[3].course_id}",
            f"No CourseRun found for {edx_enrollments_without_course_run[4].course_id}",
            "5 enrollments created, 0 updated, 5 errors",
            "Done executing Celery importing enrollments task...",
            "1 import enrollments tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_enrollments")
    def test_command_migrate_enrollments_create_dry_run(
        self, mock_get_enrollments, mock_get_enrollments_count
    ):
        """
        Test that enrollments are not created from the edx enrollments if the dry-run
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

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--enrollments", "--dry-run")

        expected = [
            "Importing data from Open edX database...",
            "Importing enrollments...",
            "Dry run: no enrollment will be imported",
            "10 enrollments to import by batch of 1000",
            "Starting Celery task, importing enrollments...",
            "Dry run: 10 enrollments would be created, 0 updated, 0 errors",
            "Done executing Celery importing enrollments task...",
            "1 import enrollments tasks launched",
        ]
        self.assertLogsContains(logger, expected)
