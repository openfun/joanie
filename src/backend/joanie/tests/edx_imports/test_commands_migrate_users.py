"""Tests for the migrate_edx command to import users from Open edX."""
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from unittest.mock import patch

from django.core.management import call_command

from joanie.core import factories
from joanie.edx_imports import edx_factories
from joanie.tests.edx_imports.base_test_commands_migrate import (
    MigrateOpenEdxBaseTestCase,
)


class MigrateOpenEdxTestCase(MigrateOpenEdxBaseTestCase):
    """Tests for the migrate_edx command to import users from Open edX."""

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_command_migrate_users_create(self, mock_get_users, mock_get_users_count):
        """
        Test that users are created from the edx users.
        """
        edx_users = edx_factories.EdxUserFactory.create_batch(10)
        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--users")

        expected = [
            "Importing data from Open edX database...",
            "Importing users...",
            "10 users to import by batch of 1000",
            "100% 10/10 : 10 users created, 0 skipped, 0 errors",
            "1 import users tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_command_migrate_users_update(self, mock_get_users, mock_get_users_count):
        """
        Test that users are updated from the edx users.
        """
        users = factories.UserFactory.create_batch(10)
        admin = factories.UserFactory.create(username="admin")
        edx_users = [
            edx_factories.EdxUserFactory.create(
                username=user.username,
            )
            for user in users
        ]
        edx_users.append(
            edx_factories.EdxUserFactory.create(
                username=admin.username,
            )
        )

        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--users")

        expected = [
            "Importing data from Open edX database...",
            "Importing users...",
            "1 users to import by batch of 1000",
            "100% 11/11 : 0 users created, 11 skipped, 0 errors",
            "1 import users tasks launched",
        ]
        self.assertLogsContains(logger, expected)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_command_migrate_users_create_dry_run(
        self, mock_get_users, mock_get_users_count
    ):
        """
        Test that users are not created from the edx users if the dry-run option is set.
        """
        edx_users = edx_factories.EdxUserFactory.create_batch(10)
        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        with self.assertLogs() as logger:
            call_command("migrate_edx", "--skip-check", "--users", "--dry-run")

        expected = [
            "Importing data from Open edX database...",
            "Importing users...",
            "Dry run: no user will be imported",
            "10 users to import by batch of 1000",
            "Dry run: 100% 10/10 : 10 users created, 0 skipped, 0 errors",
            "1 import users tasks launched",
        ]
        self.assertLogsContains(logger, expected)
