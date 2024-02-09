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
        import_universities_batch_task.delay(start=start, stop=stop, dry_run=dry_run)
    logger.info("%s import universities tasks launched", batch_count)


@app.task(bind=True)
def import_universities_batch_task(self, **kwargs):
    """
    Task to import universities from the Open edX database to the Joanie database.
    """
    logger.info("Starting Celery task, importing universities...")
    try:
        report = import_universities_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    logger.info("Done executing Celery importing universities task...")
    return report


def import_universities_batch(start, stop, dry_run=False):
    """Batch import universities from Open edX universities"""
    db = OpenEdxDB()
    universities = db.get_universities(start, stop)
    report = {
        "universities": {
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    }
    for university in universities:
        try:
            if dry_run:
                if models.Organization.objects.filter(
                    code=utils.normalize_code(university.code)
                ).exists():
                    report["universities"]["updated"] += 1
                    continue

                report["universities"]["created"] += 1
                continue

            _, created = models.Organization.objects.update_or_create(
                code=utils.normalize_code(university.code),
                defaults={
                    "title": university.name,
                    "logo": university.logo,
                },
            )
            download_and_store(university.logo, "media")
            if created:
                report["universities"]["created"] += 1
            else:
                report["universities"]["updated"] += 1
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unable to import university %s", university.code)
            logger.exception(exc)
            report["universities"]["errors"] += 1

    import_string = "%s universities created, %s updated, %s errors"
    if dry_run:
        import_string = (
            "Dry run: %s universities would be created, %s updated, %s errors"
        )

    logger.info(
        import_string,
        report["universities"]["created"],
        report["universities"]["updated"],
        report["universities"]["errors"],
    )

    return report
