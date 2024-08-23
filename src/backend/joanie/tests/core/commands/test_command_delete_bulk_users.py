"""Test suite for the management command 'delete_bulk_users'"""

from django.core.management import call_command
from django.test import TestCase, override_settings

from django_redis import get_redis_connection

from joanie.core import factories, models

JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY = "test_delete_bulk_users"


@override_settings(
    JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY=JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY
)
class DeleteBulkUsersCommandTestCase(TestCase):
    """Test management command 'delete_bulk_users'"""

    def test_delete_bulk_users_without_limit(self):
        """
        Test delete_bulk_users command without limit option should delete all users in the set
        """
        redis_connection = get_redis_connection("redis")
        users = factories.UserFactory.create_batch(10)
        for user in users:
            redis_connection.sadd(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY, user.username)

        call_command("delete_bulk_users")

        self.assertEqual(models.User.objects.count(), 0)
        self.assertFalse(
            redis_connection.exists(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY)
        )

    def test_delete_bulk_users_with_limit(self):
        """
        Test delete_bulk_users command with limit option should delete only the number of users
        specified in the limit option
        """
        redis_connection = get_redis_connection("redis")
        users = factories.UserFactory.create_batch(10)
        for user in users:
            redis_connection.sadd(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY, user.username)

        call_command("delete_bulk_users", limit=5)

        self.assertEqual(models.User.objects.count(), 5)
        self.assertTrue(redis_connection.exists(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY))
        self.assertEqual(
            redis_connection.scard(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY), 5
        )

    def test_delete_bulk_users_with_limit_greater_than_users(self):
        """
        Test delete_bulk_users command with limit option greater than the number of users in the set
        should delete all users in the set
        """
        redis_connection = get_redis_connection("redis")
        users = factories.UserFactory.create_batch(10)
        for user in users:
            redis_connection.sadd(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY, user.username)

        call_command("delete_bulk_users", limit=15)

        self.assertEqual(models.User.objects.count(), 0)
        self.assertFalse(
            redis_connection.exists(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY)
        )
        self.assertEqual(
            redis_connection.scard(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY), 0
        )

    def test_delete_bulk_users_non_exising_set(self):
        """
        Test delete_bulk_users command with non existing set should not raise any error
        """
        self.assertEqual(models.User.objects.count(), 0)
        self.assertFalse(
            get_redis_connection("redis").exists(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY)
        )

        call_command("delete_bulk_users")

        self.assertEqual(models.User.objects.count(), 0)
        self.assertFalse(
            get_redis_connection("redis").exists(JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY)
        )
