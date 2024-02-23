"""Celery tasks for importing data from the Open edX database to the Joanie database."""
# pylint: disable=too-many-locals

from logging import getLogger

from django.contrib.auth.hashers import make_password

from joanie.celery_app import app
from joanie.core import models
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import extract_language_code, format_date

logger = getLogger(__name__)


def import_users(batch_size=1000, offset=0, limit=0, dry_run=False):
    """Import users from Open edX auth_user"""
    db = OpenEdxDB()
    users_count = db.get_users_count(offset, limit)
    if dry_run:
        logger.info("Dry run: no user will be imported")
    logger.info("%s users to import by batch of %s", users_count, batch_size)

    batch_count = 0
    for current_user_index in range(0, users_count, batch_size):
        batch_count += 1
        start = current_user_index + offset
        stop = current_user_index + batch_size
        import_users_batch_task.delay(start=start, stop=stop, dry_run=dry_run)
    logger.info("%s import users tasks launched", batch_count)


@app.task(bind=True)
def import_users_batch_task(self, **kwargs):
    """
    Task to import users from the Open edX database to the Joanie database.
    """
    logger.info("Starting Celery task, importing users...")
    try:
        report = import_users_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    logger.info("Done executing Celery importing users task...")
    return report


def import_users_batch(start, stop, dry_run=False):
    """Batch import users from Open edX auth_user"""
    db = OpenEdxDB()
    report = {"users": {"created": 0, "errors": 0}}
    users = db.get_users(start, stop)
    users_to_create = []

    for edx_user in users:
        if models.User.objects.filter(username=edx_user.username).exists():
            logger.info("User %s already exists", edx_user.username)
            continue

        users_to_create.append(
            models.User(
                username=edx_user.username,
                email=edx_user.email,
                password=make_password(None),
                first_name=edx_user.auth_userprofile.name,
                is_active=edx_user.is_active,
                is_staff=edx_user.is_staff,
                is_superuser=edx_user.is_superuser,
                date_joined=format_date(edx_user.date_joined),
                last_login=format_date(edx_user.last_login),
                language=extract_language_code(edx_user),
            )
        )

    import_string = "%s users created, %s errors"
    if dry_run:
        import_string = "Dry run: %s users would be created, %s errors"
        report["users"]["created"] += len(users_to_create)
    else:
        users_created = models.User.objects.bulk_create(users_to_create)
        report["users"]["created"] += len(users_created)

    logger.info(
        import_string,
        report["users"]["created"],
        report["users"]["errors"],
    )

    return report
