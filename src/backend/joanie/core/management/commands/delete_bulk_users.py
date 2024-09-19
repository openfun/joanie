"""
Management command getting all users to delete from a redis set and dispatching a task to delete
them.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from django_redis import get_redis_connection

from joanie.core.tasks import delete_user


class Command(BaseCommand):
    """
    This command is responsible to delete all the users references in redis in the set
    with key settings.JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY.

    WARNING: Without the --limit option, all users in the set are deleted at once. Be careful, if
    hundreds of thousands users are in the set, it can be a long process.
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--redis-alias",
            type=str,
            help="Redis alias name from CACHES setting",
            default="redis",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help=(
                "Number of users to pop from the redis set. If not used, "
                "all users in the set are deleted at once."
            ),
        )

    def handle(self, *args, **options):
        redis_connection = get_redis_connection(options.get("redis_alias"))

        if options.get("limit"):
            users = redis_connection.spop(
                settings.JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY, options.get("limit")
            )
        else:
            users = redis_connection.smembers(
                settings.JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY
            )
            redis_connection.delete(settings.JOANIE_DELETE_BULK_USERS_REDIS_SET_KEY)

        for username in users:
            # dispatch in a task
            delete_user.delay(
                username.decode("utf-8") if isinstance(username, bytes) else username
            )
