"""Tests for the import_users task."""
# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from os.path import dirname, join, realpath
from unittest.mock import patch

from django.contrib.auth.hashers import is_password_usable
from django.test import TestCase, override_settings

from joanie.core import factories, models
from joanie.edx_imports import edx_factories
from joanie.edx_imports.tasks.users import import_users
from joanie.edx_imports.utils import extract_language_code, make_date_aware

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
class EdxImportUsersTestCase(TestCase):
    """Tests for the import_users task."""

    maxDiff = None

    def tearDown(self):
        """Tear down the test case."""
        edx_factories.session.rollback()

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_import_users_create(self, mock_get_users, mock_get_users_count):
        """
        Test that users are created from the edx users.
        """
        edx_users = edx_factories.EdxUserFactory.create_batch(10)
        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        import_users()

        self.assertEqual(models.User.objects.count(), len(edx_users))
        for edx_user in edx_users:
            user = models.User.objects.get(username=edx_user.username)
            self.assertEqual(user.email, edx_user.email)
            self.assertNotEqual(user.password, edx_user.password)
            self.assertFalse(is_password_usable(user.password))
            self.assertEqual(user.first_name, edx_user.auth_userprofile.name)
            self.assertEqual(user.last_name, "")
            self.assertEqual(user.is_active, edx_user.is_active)
            self.assertEqual(user.is_staff, edx_user.is_staff)
            self.assertEqual(user.is_superuser, edx_user.is_superuser)
            self.assertEqual(user.date_joined, make_date_aware(edx_user.date_joined))
            self.assertEqual(user.last_login, make_date_aware(edx_user.last_login))
            self.assertEqual(user.language, extract_language_code(edx_user))

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_import_users_update(self, mock_get_users, mock_get_users_count):
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

        import_users()

        self.assertEqual(models.User.objects.count(), len(edx_users))
        for edx_user in edx_users:
            user = models.User.objects.get(username=edx_user.username)
            language_code = extract_language_code(edx_user)
            if user.username == "admin":
                self.assertEqual(user.email, admin.email)
                self.assertEqual(user.password, admin.password)
                self.assertEqual(user.first_name, admin.first_name)
                self.assertEqual(user.last_name, admin.last_name)
                self.assertEqual(user.is_active, admin.is_active)
                self.assertEqual(user.is_staff, admin.is_staff)
                self.assertEqual(user.is_superuser, admin.is_superuser)
                self.assertEqual(user.date_joined, admin.date_joined)
                self.assertEqual(user.last_login, admin.last_login)
                self.assertEqual(user.language, admin.language)
            else:
                self.assertEqual(user.email, edx_user.email)
                self.assertNotEqual(user.password, edx_user.password)
                self.assertFalse(is_password_usable(user.password))
                self.assertEqual(user.first_name, edx_user.auth_userprofile.name)
                self.assertEqual(user.last_name, "")
                self.assertEqual(user.is_active, edx_user.is_active)
                self.assertEqual(user.is_staff, edx_user.is_staff)
                self.assertEqual(user.is_superuser, edx_user.is_superuser)
                self.assertEqual(
                    user.date_joined, make_date_aware(edx_user.date_joined)
                )
                self.assertEqual(user.last_login, make_date_aware(edx_user.last_login))
                self.assertEqual(user.language, language_code)

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_import_users_create_dry_run(self, mock_get_users, mock_get_users_count):
        """
        Test that no user is created from the edx users in dry run mode.
        """
        edx_users = edx_factories.EdxUserFactory.create_batch(10)
        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        import_users(dry_run=True)

        self.assertEqual(models.User.objects.count(), 0)
