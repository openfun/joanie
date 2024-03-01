"""Celery tasks for importing data from the Open edX database to the Joanie database."""
# pylint: disable=too-many-locals

from logging import getLogger

from django.conf import settings

from parler.utils import get_language_settings

from joanie.celery_app import app
from joanie.core import models
from joanie.core.utils import normalize_code
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import (
    check_language_code,
    extract_course_number,
    format_date,
    format_percent,
    make_date_aware,
)

logger = getLogger(__name__)


def import_course_runs(batch_size=1000, offset=0, limit=0, dry_run=False):
    """Import course runs and courses from Open edX course_overviews"""
    db = OpenEdxDB()
    course_overviews_count = db.get_course_overviews_count(offset, limit)
    if dry_run:
        logger.info("Dry run: no course run will be imported")
    logger.info(
        "%s course_overviews to import by batch of %s",
        course_overviews_count,
        batch_size,
    )

    batch_count = 0
    for current_course_overview_index in range(0, course_overviews_count, batch_size):
        batch_count += 1
        start = current_course_overview_index + offset
        stop = current_course_overview_index + batch_size
        import_course_runs_batch_task.delay(
            start=start, stop=stop, total=course_overviews_count, dry_run=dry_run
        )
    logger.info("%s import course runs tasks launched", batch_count)


@app.task(bind=True)
def import_course_runs_batch_task(self, **kwargs):
    """
    Task to import course runs from the Open edX database to the Joanie database.
    """
    try:
        report = import_course_runs_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    return report


def import_course_runs_batch(start, stop, total, dry_run=False):
    """Batch import course runs and courses from Open edX course_overviews"""
    db = OpenEdxDB()
    report = {
        "courses": {
            "created": 0,
            "skipped": 0,
            "errors": 0,
        },
        "course_runs": {
            "created": 0,
            "skipped": 0,
            "errors": 0,
        },
    }
    edx_course_overviews = db.get_course_overviews(start, stop)
    for edx_course_overview in edx_course_overviews:
        # Select LMS from resource link
        resource_link = (
            f"https://{settings.EDX_DOMAIN}/courses/{edx_course_overview.id}/course"
        )

        try:
            target_course_run = models.CourseRun.objects.only("pk").get(
                resource_link=resource_link
            )
        except models.CourseRun.DoesNotExist:
            target_course_run = None

        language_code = check_language_code(edx_course_overview.course.language)

        edx_course_run_dict = {
            "resource_link": resource_link,
            "start": format_date(edx_course_overview.start),
            "end": format_date(edx_course_overview.end),
            "enrollment_start": format_date(edx_course_overview.enrollment_start),
            "enrollment_end": format_date(edx_course_overview.enrollment_end),
            "languages": [language_code],
            "is_listed": True,
        }

        if target_course_run:
            course_run = models.CourseRun.objects.get(pk=target_course_run.pk)
        else:
            course_number = extract_course_number(edx_course_overview.id)
            try:
                course = models.Course.objects.get(code=course_number)
            except models.Course.DoesNotExist:
                if not dry_run:
                    course = models.Course.objects.create(
                        created_on=format_date(edx_course_overview.created),
                        code=course_number,
                        title=edx_course_overview.display_name or course_number,
                    )
                    relations = (
                        edx_course_overview.course.courses_courseuniversityrelation
                    )
                    course.organizations.set(
                        models.Organization.objects.filter(
                            code__in=[
                                normalize_code(relation.university.code)
                                for relation in relations
                            ]
                        )
                    )
                    course.created_on = make_date_aware(edx_course_overview.created)
                    course.save()
                report["courses"]["created"] += 1

            if not dry_run:
                # Instantiate a new course run
                course_run = models.CourseRun.objects.create(
                    **edx_course_run_dict,
                    course=course,
                )
                course_run.created_on = make_date_aware(edx_course_overview.created)
                course_run.save()
            report["course_runs"]["created"] += 1

        if not dry_run:
            if title := edx_course_overview.display_name:
                course_run.set_current_language(
                    get_language_settings(language_code).get("code")
                )
                course_run.title = title
            course_run.created_on = make_date_aware(edx_course_overview.created)
            course_run.save()

    courses_import_string = "%s courses created, %s skipped, %s errors"
    course_runs_import_string = (
        "%s %s/%s : %s course runs created, %s skipped, %s errors"
    )
    if dry_run:
        courses_import_string = "Dry run: " + courses_import_string
        course_runs_import_string = "Dry run: " + course_runs_import_string

    stop = min(stop, total)
    percent = format_percent(stop, total)
    logger.info(
        courses_import_string,
        report["courses"]["created"],
        report["courses"]["skipped"],
        report["courses"]["errors"],
    )
    logger.info(
        course_runs_import_string,
        percent,
        stop,
        total,
        report["course_runs"]["created"],
        report["course_runs"]["skipped"],
        report["course_runs"]["errors"],
    )

    return (
        courses_import_string
        % (
            report["course_runs"]["created"],
            report["course_runs"]["skipped"],
            report["course_runs"]["errors"],
        )
        + ", "
        + course_runs_import_string
        % (
            percent,
            stop,
            total,
            report["course_runs"]["created"],
            report["course_runs"]["skipped"],
            report["course_runs"]["errors"],
        )
    )
