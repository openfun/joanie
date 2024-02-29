"""Celery tasks for importing Open edX universities to Joanie organizations."""

from logging import getLogger

from joanie.celery_app import app
from joanie.core import models, utils
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import download_and_store

logger = getLogger(__name__)


def import_universities(batch_size=1000, offset=0, limit=0, dry_run=False):
    """Import organizations from Open edX universities"""
    db = OpenEdxDB()
    universities_count = db.get_universities_count(offset, limit)
    if dry_run:
        logger.info("Dry run: no university will be imported")
    logger.info(
        "%s universities to import by batch of %s", universities_count, batch_size
    )

    batch_count = 0
    for current_university_index in range(0, universities_count, batch_size):
        batch_count += 1
        start = current_university_index + offset
        stop = current_university_index + batch_size
        import_universities_batch_task.delay(
            start=start, stop=stop, total=universities_count, dry_run=dry_run
        )
    logger.info("%s import universities tasks launched", batch_count)


@app.task(bind=True)
def import_universities_batch_task(self, **kwargs):
    """
    Task to import universities from the Open edX database to the Joanie database.
    """
    try:
        report = import_universities_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    return report


def import_universities_batch(start, stop, total, dry_run=False):
    """Batch import universities from Open edX universities"""
    db = OpenEdxDB()
    universities = db.get_universities(start, stop)
    report = {
        "universities": {
            "created": 0,
            "skipped": 0,
            "errors": 0,
        }
    }
    for university in universities:
        try:
            if models.Organization.objects.filter(
                code=utils.normalize_code(university.code)
            ).exists():
                report["universities"]["skipped"] += 1
                continue
            if dry_run:
                report["universities"]["created"] += 1
                continue

            logo_path = download_and_store(university.logo, "media")
            models.Organization.objects.create(
                code=utils.normalize_code(university.code),
                title=university.name,
                logo=logo_path,
            )
            report["universities"]["created"] += 1
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unable to import university %s", university.code)
            logger.exception(exc)
            report["universities"]["errors"] += 1

    import_string = "%s-%s/%s %s universities created, %s skipped, %s errors"
    if dry_run:
        import_string = "Dry run: " + import_string

    logger.info(
        import_string,
        start,
        stop,
        total,
        report["universities"]["created"],
        report["universities"]["skipped"],
        report["universities"]["errors"],
    )

    return report
