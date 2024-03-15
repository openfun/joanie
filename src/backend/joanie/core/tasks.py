"""Celery tasks for the `core` app of Joanie"""

from logging import getLogger

from django.core.cache import cache
from django.core.management import call_command

from joanie.celery_app import app
from joanie.core import helpers

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


@app.task
def generate_certificates_task(order_ids, cache_key):
    """
    Task to generate certificates from orders. It calls the helper command to generate
    certificates from an Order queryset. Once done, it cleans up the data in cache.
    """
    logger.info("Starting Celery task, generating certificates...")
    try:
        helpers.generate_certificates_for_orders(orders=order_ids)
    finally:
        cache.delete(cache_key)
    logger.info("Done executing Celery generating certificates task...")
