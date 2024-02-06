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
    report = {
        "users": {
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    }
    users = db.get_users(start, stop)
    users_to_create = []
    users_to_update = []

    for edx_user in users:
        if edx_user.username == "admin":
            continue
        last_login = format_date(edx_user.last_login)
        date_joined = format_date(edx_user.date_joined)
        language_code = extract_language_code(edx_user)
        try:
            user = models.User.objects.get(username=edx_user.username)
            user.email = edx_user.email
            user.password = make_password(None)
            user.first_name = edx_user.auth_userprofile.name
            user.is_active = edx_user.is_active
            user.is_staff = edx_user.is_staff
            user.is_superuser = edx_user.is_superuser
            user.date_joined = date_joined
            user.last_login = last_login
            user.language = language_code
            users_to_update.append(user)
        except models.User.DoesNotExist:
            users_to_create.append(
                models.User(
                    username=edx_user.username,
                    email=edx_user.email,
                    password=make_password(None),
                    first_name=edx_user.auth_userprofile.name,
                    is_active=edx_user.is_active,
                    is_staff=edx_user.is_staff,
                    is_superuser=edx_user.is_superuser,
                    date_joined=date_joined,
                    last_login=last_login,
                    language=language_code,
                )
            )

    import_string = "%s users created, %s updated, %s errors"
    if not dry_run:
        users_created = models.User.objects.bulk_create(users_to_create)
        report["users"]["created"] += len(users_created)

        users_updated = models.User.objects.bulk_update(
            users_to_update,
            [
                "email",
                "password",
                "first_name",
                "last_name",
                "is_active",
                "is_staff",
                "is_superuser",
                "date_joined",
                "last_login",
                "language",
            ],
        )
        report["users"]["updated"] += users_updated
    else:
        import_string = "Dry run: %s users would be created, %s updated, %s errors"
        report["users"]["created"] += len(users_to_create)
        report["users"]["updated"] += len(users_to_update)

    logger.info(
        import_string,
        report["users"]["created"],
        report["users"]["updated"],
        report["users"]["errors"],
    )

    return report
