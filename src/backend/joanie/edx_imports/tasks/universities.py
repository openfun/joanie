"""Celery tasks for importing Open edX universities to Joanie organizations."""

from logging import getLogger

from joanie.celery_app import app
from joanie.core import models, utils
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import download_and_store, format_percent

logger = getLogger(__name__)


def import_universities(batch_size=1000, global_offset=0, import_size=0, dry_run=False):
    """Import organizations from Open edX universities"""
    db = OpenEdxDB()
    total = db.get_universities_count(global_offset, import_size)
    if dry_run:
        logger.info("Dry run: no university will be imported")
    logger.info("%s universities to import by batch of %s", total, batch_size)

    batch_count = 0
    for batch_offset in range(global_offset, global_offset + total, batch_size):
        batch_count += 1
        import_universities_batch_task.delay(
            batch_offset=batch_offset,
            batch_size=batch_size,
            total=total,
            dry_run=dry_run,
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


def import_universities_batch(batch_offset, batch_size, total, dry_run=False):
    """Batch import universities from Open edX universities"""
    db = OpenEdxDB()
    universities = db.get_universities(batch_offset, batch_size)
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

    import_string = "%s %s/%s : %s universities created, %s skipped, %s errors"
    if dry_run:
        import_string = "Dry run: " + import_string

    total_processed = (
        batch_offset
        + report["universities"]["created"]
        + report["universities"]["skipped"]
        + report["universities"]["errors"]
    )
    percent = format_percent(total_processed, total)
    logger.info(
        import_string,
        percent,
        total_processed,
        total,
        report["universities"]["created"],
        report["universities"]["skipped"],
        report["universities"]["errors"],
    )

    return import_string % (
        percent,
        total_processed,
        total,
        report["universities"]["created"],
        report["universities"]["skipped"],
        report["universities"]["errors"],
    )
