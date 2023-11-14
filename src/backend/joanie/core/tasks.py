"""Celery tasks for the `core` app of Joanie"""
from logging import getLogger

from django.core.management import call_command

from joanie.celery_app import app

logger = getLogger(__name__)


@app.task
def generate_zip_archive_task(options):
    """
    Task to generate the ZIP archive of the signed contracts.
    It calls the django custom command `generate_zip_archive_of_contracts` with the parsed
    options.
    """
    logger.info("Starting Celery task, generating a ZIP Archive...")
    call_command("generate_zip_archive_of_contracts", **options)
    logger.info("Done executing Celery generating a ZIP Archive task...")
