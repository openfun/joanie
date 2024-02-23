"""Celery tasks for importing Open edX certificates to Joanie organizations."""

# pylint: disable=too-many-locals,too-many-statements
# ruff: noqa: SLF001,PLR0915,PLR0912

from logging import getLogger

from django.conf import settings
from django.core.files.storage import default_storage

from hashids import Hashids

from joanie.celery_app import app
from joanie.core import models
from joanie.core.enums import CERTIFICATE, DEGREE
from joanie.core.utils import image_to_base64
from joanie.edx_imports import edx_mongodb
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import download_and_store, make_date_aware
from joanie.lms_handler.backends.openedx import OPENEDX_MODE_VERIFIED

logger = getLogger(__name__)


def import_certificates(batch_size=1000, offset=0, limit=0, dry_run=False):
    """Import organizations from Open edX certificates"""
    db = OpenEdxDB()
    certificates_count = db.get_certificates_count(offset, limit)
    if dry_run:
        logger.info("Dry run: no certificate will be imported")
    logger.info(
        "%s certificates to import by batch of %s", certificates_count, batch_size
    )

    batch_count = 0
    for current_certificate_index in range(0, certificates_count, batch_size):
        batch_count += 1
        start = current_certificate_index + offset
        stop = current_certificate_index + batch_size
        import_certificates_batch_task.delay(start=start, stop=stop, dry_run=dry_run)
    logger.info("%s import certificates tasks launched", batch_count)


@app.task(bind=True)
def import_certificates_batch_task(self, **kwargs):
    """
    Task to import certificates from the Open edX database to the Joanie database.
    """
    logger.info("Starting Celery task, importing certificates...")
    try:
        report = import_certificates_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    logger.info("Done executing Celery importing certificates task...")
    return report


def import_certificates_batch(start, stop, dry_run=False):
    """Batch import certificates from Open edX certificates_generatedcertificate"""
    db = OpenEdxDB()
    report = {
        "certificates": {
            "created": 0,
            "errors": 0,
        }
    }
    hashids = Hashids(salt=settings.EDX_SECRET)
    certificates = db.get_certificates(start, stop)
    certificates_to_create = []

    for edx_certificate in certificates:
        try:
            enrollment = models.Enrollment.objects.get(
                user__username=edx_certificate.user.username,
                course_run__resource_link__icontains=edx_certificate.course_id,
            )
        except models.Enrollment.DoesNotExist:
            report["certificates"]["errors"] += 1
            logger.error(
                "No Enrollment found for %s %s",
                edx_certificate.user.username,
                edx_certificate.course_id,
            )
            continue

        organization_code, signatory = edx_mongodb.get_enrollment(
            edx_certificate.course_id
        )

        if not organization_code:
            report["certificates"]["errors"] += 1
            logger.error(
                "No organization found in mongodb for %s", edx_certificate.course_id
            )
            continue

        try:
            organization = models.Organization.objects.get(code=organization_code)
        except models.Organization.DoesNotExist:
            report["certificates"]["errors"] += 1
            logger.error("No organization found for %s", organization_code)
            continue

        verification_hash = hashids.encode(edx_certificate.id)

        signature = None
        signatory_name = None
        if signatory:
            signature_image_path = signatory.get("signature_image_path")
            if signature_image_path.startswith("/"):
                signature_image_path = signature_image_path[1:]
            signature_path = download_and_store(signature_image_path)
            signature = image_to_base64(default_storage.path(signature_path))
            signatory_name = signatory.get("name")

        certificate_context = {
            "signatory": signatory,
            "verification_hash": verification_hash,
        }

        title_object = enrollment.course_run.course

        for language, _ in settings.LANGUAGES:
            certificate_context[language] = {
                "course": {
                    "name": title_object.safe_translation_getter(
                        "title", language_code=language
                    ),
                },
                "organizations": [
                    {
                        "name": organization.safe_translation_getter(
                            "title", language_code=language
                        ),
                        "representative": signatory_name,
                        "signature": signature,
                        "logo": image_to_base64(organization.logo),
                    }
                ],
            }

        certificate_name = (
            DEGREE if edx_certificate.mode == OPENEDX_MODE_VERIFIED else CERTIFICATE
        )
        if models.Certificate.objects.filter(enrollment=enrollment).exists():
            logger.info(
                "Certificate for %s in %s already exists",
                edx_certificate.user.username,
                edx_certificate.course_id,
            )
            continue

        certificates_to_create.append(
            models.Certificate(
                certificate_definition=models.CertificateDefinition.objects.get(
                    name=certificate_name
                ),
                organization=organization,
                enrollment=enrollment,
                issued_on=make_date_aware(edx_certificate.created_date),
                localized_context=certificate_context,
            )
        )

    import_string = "%s certificates created, %s errors"
    if not dry_run:
        certificate_issued_on_field = models.Certificate._meta.get_field("issued_on")
        certificate_issued_on_field.auto_now = False
        certificate_issued_on_field.editable = True

        certificates_created = models.Certificate.objects.bulk_create(
            certificates_to_create
        )
        report["certificates"]["created"] += len(certificates_created)

        certificate_issued_on_field.auto_now = True
        certificate_issued_on_field.editable = False
    else:
        import_string = "Dry run: %s certificates would be created, %s errors"
        report["certificates"]["created"] += len(certificates_to_create)

    logger.info(
        import_string,
        report["certificates"]["created"],
        report["certificates"]["errors"],
    )

    return report
