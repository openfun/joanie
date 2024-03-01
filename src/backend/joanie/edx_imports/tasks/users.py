"""Celery tasks for importing data from the Open edX database to the Joanie database."""
# ruff: noqa: SLF001
# pylint: disable=too-many-locals

from logging import getLogger

from django.contrib.auth.hashers import make_password

from joanie.celery_app import app
from joanie.core import models
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import extract_language_code, format_date, format_percent

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
        if limit:
            stop = min(stop, limit)
        import_users_batch_task.delay(
            start=start, stop=stop, total=users_count, dry_run=dry_run
        )
    logger.info("%s import users tasks launched", batch_count)


@app.task(bind=True)
def import_users_batch_task(self, **kwargs):
    """
    Task to import users from the Open edX database to the Joanie database.
    """
    try:
        report = import_users_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    return report


def import_users_batch(start, stop, total, dry_run=False):
    """Batch import users from Open edX auth_user"""
    db = OpenEdxDB()
    report = {"users": {"created": 0, "skipped": 0, "errors": 0}}
    users = db.get_users(start, stop)
    users_to_create = []

    for edx_user in users:
        if models.User.objects.filter(username=edx_user.username).exists():
            report["users"]["skipped"] += 1
            continue

        username = edx_user.username.strip()
        email = edx_user.email.strip()
        first_name = edx_user.auth_userprofile.name.strip()
        if len(username) > models.User._meta.get_field("username").max_length:
            report["users"]["errors"] += 1
            logger.error("Username too long: %s", username)
            continue

        if len(email) > models.User._meta.get_field("email").max_length:
            report["users"]["errors"] += 1
            logger.error("Email too long: %s", email)
            continue

        if len(first_name) > models.User._meta.get_field("first_name").max_length:
            report["users"]["errors"] += 1
            logger.error("First name too long: %s", first_name)
            continue

        users_to_create.append(
            models.User(
                username=username,
                email=email,
                password=make_password(None),
                first_name=first_name,
                is_active=edx_user.is_active,
                is_staff=edx_user.is_staff,
                is_superuser=edx_user.is_superuser,
                date_joined=format_date(edx_user.date_joined),
                last_login=format_date(edx_user.last_login),
                language=extract_language_code(edx_user),
            )
        )

    import_string = "%s %s/%s : %s users created, %s skipped, %s errors"
    if dry_run:
        import_string = "Dry run: " + import_string
        report["users"]["created"] += len(users_to_create)
    else:
        users_created = models.User.objects.bulk_create(users_to_create)
        report["users"]["created"] += len(users_created)

    stop = min(stop, total)
    percent = format_percent(stop, total)
    logger.info(
        import_string,
        percent,
        stop,
        total,
        report["users"]["created"],
        report["users"]["skipped"],
        report["users"]["errors"],
    )

    return import_string % (
        percent,
        stop,
        total,
        report["users"]["created"],
        report["users"]["skipped"],
        report["users"]["errors"],
    )
