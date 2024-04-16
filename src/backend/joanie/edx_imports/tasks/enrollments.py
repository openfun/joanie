"""Celery tasks for importing data from the Open edX database to the Joanie database."""
# pylint: disable=too-many-locals, too-many-branches, broad-exception-caught
# ruff: noqa: SLF001,PLR0912,BLE001

from logging import getLogger

from joanie.celery_app import app
from joanie.core import models
from joanie.core.enums import ENROLLMENT_STATE_SET
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import format_percent, make_date_aware

logger = getLogger(__name__)


def import_enrollments(
    batch_size=1000, global_offset=0, import_size=0, course_id=None, dry_run=False
):
    """Import enrollments from Open edX student_course_enrollment"""
    db = OpenEdxDB()
    total = db.get_enrollments_count(global_offset, import_size, course_id=course_id)
    if dry_run:
        logger.info("Dry run: no enrollment will be imported")
    logger.info("%s enrollments to import by batch of %s", total, batch_size)

    batch_count = 0
    for batch_offset in range(global_offset, global_offset + total, batch_size):
        batch_count += 1
        import_enrollments_batch_task.delay(
            batch_offset=batch_offset,
            batch_size=batch_size,
            total=total,
            course_id=course_id,
            dry_run=dry_run,
        )
    logger.info("%s import enrollments tasks launched", batch_count)


@app.task(bind=True)
def import_enrollments_batch_task(self, **kwargs):
    """
    Task to import enrollments from the Open edX database to the Joanie database.
    """
    try:
        report = import_enrollments_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    return report


def import_enrollments_batch(batch_offset, batch_size, total, course_id, dry_run=False):
    """Batch import enrollments from Open edX student_course_enrollment"""
    db = OpenEdxDB()
    report = {
        "enrollments": {
            "created": 0,
            "skipped": 0,
            "errors": 0,
        }
    }
    enrollments = db.get_enrollments(batch_offset, batch_size, course_id=course_id)
    enrollments_to_create = []

    for edx_enrollment in enrollments:
        try:
            try:
                course_run = models.CourseRun.objects.only("pk").get(
                    resource_link__icontains=edx_enrollment.course_id
                )
            except models.CourseRun.DoesNotExist:
                report["enrollments"]["errors"] += 1
                logger.error(
                    "No CourseRun found for %s",
                    edx_enrollment.course_id,
                    extra={"context": {"edx_enrollment": edx_enrollment.safe_dict()}},
                )
                continue
            except models.CourseRun.MultipleObjectsReturned:
                try:
                    course_run = models.CourseRun.objects.only("pk").get(
                        resource_link__icontains=f"{edx_enrollment.course_id}/info"
                    )
                except models.CourseRun.DoesNotExist:
                    report["enrollments"]["errors"] += 1
                    logger.error(
                        "No CourseRun found for %s",
                        edx_enrollment.course_id,
                        extra={
                            "context": {"edx_enrollment": edx_enrollment.safe_dict()}
                        },
                    )
                    continue

            user_name = edx_enrollment.user.username
            try:
                user = models.User.objects.only("pk").get(username=user_name)
            except models.User.DoesNotExist:
                report["enrollments"]["errors"] += 1
                logger.error(
                    "No User found for %s",
                    user_name,
                    extra={
                        "context": {
                            "edx_enrollment": edx_enrollment.safe_dict(),
                            "edx_user": edx_enrollment.user.safe_dict(),
                        }
                    },
                )
                continue

            if models.Enrollment.objects.filter(
                course_run=course_run, user=user
            ).exists():
                report["enrollments"]["skipped"] += 1
                continue

            enrollments_to_create.append(
                models.Enrollment(
                    course_run=course_run,
                    user=user,
                    is_active=edx_enrollment.is_active,
                    created_on=make_date_aware(edx_enrollment.created),
                    state=ENROLLMENT_STATE_SET,
                )
            )
        except Exception as e:
            report["enrollments"]["errors"] += 1
            logger.error(
                "Error creating Enrollment: %s",
                e,
                extra={
                    "context": {
                        "exception": e,
                        "edx_enrollment": edx_enrollment.safe_dict(),
                    }
                },
            )
            continue

    import_string = "%s %s/%s : %s enrollments created, %s skipped, %s errors"
    if not dry_run:
        enrollment_created_on_field = models.Enrollment._meta.get_field("created_on")
        enrollment_created_on_field.auto_now_add = False
        enrollment_created_on_field.editable = True

        enrollments_created = models.Enrollment.objects.bulk_create(
            enrollments_to_create, ignore_conflicts=True
        )
        report["enrollments"]["created"] += len(enrollments_created)

        enrollment_created_on_field.auto_now_add = True
        enrollment_created_on_field.editable = False
    else:
        import_string = "Dry run: " + import_string
        report["enrollments"]["created"] += len(enrollments_to_create)

    total_processed = (
        batch_offset
        + report["enrollments"]["created"]
        + report["enrollments"]["skipped"]
        + report["enrollments"]["errors"]
    )
    percent = format_percent(total_processed, total)
    logger.info(
        import_string,
        percent,
        total_processed,
        total,
        report["enrollments"]["created"],
        report["enrollments"]["skipped"],
        report["enrollments"]["errors"],
    )

    return import_string % (
        percent,
        total_processed,
        total,
        report["enrollments"]["created"],
        report["enrollments"]["skipped"],
        report["enrollments"]["errors"],
    )
