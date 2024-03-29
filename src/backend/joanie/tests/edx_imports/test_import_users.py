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
        # User with no profile should not be included
        edx_factories.EdxUserFactory(auth_userprofile=None)
        # User with no preference should be included
        edx_user_no_preference = edx_factories.EdxUserFactory(
            user_api_userpreference=None
        )
        edx_users.append(edx_user_no_preference)

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
            if edx_user == edx_user_no_preference:
                self.assertEqual(user.language, "en-us")
            else:
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
        created_user = edx_factories.EdxUserFactory.create(
            username=admin.username,
        )
        edx_users.append(created_user)

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
            elif user.username == created_user.username:
                self.assertEqual(user.email, created_user.email)
                self.assertNotEqual(user.password, created_user.password)
                self.assertFalse(is_password_usable(user.password))
                self.assertEqual(user.first_name, created_user.auth_userprofile.name)
                self.assertEqual(user.last_name, "")
                self.assertEqual(user.is_active, created_user.is_active)
                self.assertEqual(user.is_staff, created_user.is_staff)
                self.assertEqual(user.is_superuser, created_user.is_superuser)
                self.assertEqual(
                    user.date_joined, make_date_aware(created_user.date_joined)
                )
                self.assertEqual(
                    user.last_login, make_date_aware(created_user.last_login)
                )
                self.assertEqual(user.language, language_code)
            else:
                self.assertNotEqual(user.email, edx_user.email)
                self.assertNotEqual(user.password, edx_user.password)
                self.assertTrue(is_password_usable(user.password))

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

    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users_count")
    @patch("joanie.edx_imports.edx_database.OpenEdxDB.get_users")
    def test_import_users_create_long_usernames(
        self, mock_get_users, mock_get_users_count
    ):
        """
        Test that users are created from the edx users.
        """
        edx_users = []
        edx_users.append(
            edx_factories.EdxUserFactory(
                username="a" * 255,
                email="a" * 255 + "@example.com",
                auth_userprofile__name="a" * 255,
            )
        )
        edx_users.append(
            edx_factories.EdxUserFactory(
                username=" some username with spaces" + " " * 255,
                email=" username@example.com" + " " * 255,
                auth_userprofile__name=" some username with spaces" + " " * 255,
            )
        )

        mock_get_users.return_value = edx_users
        mock_get_users_count.return_value = len(edx_users)

        import_users()

        self.assertEqual(models.User.objects.count(), 1)

        user = models.User.objects.get()
        self.assertEqual(user.username, "some username with spaces")
        self.assertEqual(user.email, "username@example.com")
        self.assertEqual(user.first_name, "some username with spaces")
