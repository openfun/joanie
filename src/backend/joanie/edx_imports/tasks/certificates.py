"""Celery tasks for importing Open edX certificates to Joanie organizations."""

# pylint: disable=too-many-locals,too-many-statements,too-many-branches
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
from joanie.edx_imports.utils import (
    download_and_store,
    extract_organization_code,
    format_percent,
    make_date_aware,
)
from joanie.lms_handler.backends.openedx import OPENEDX_MODE_VERIFIED

logger = getLogger(__name__)


def import_certificates(
    batch_size=1000, global_offset=0, import_size=0, course_id=None, dry_run=False
):
    """Import organizations from Open edX certificates"""
    db = OpenEdxDB()
    total = db.get_certificates_count(global_offset, import_size, course_id=course_id)
    if dry_run:
        logger.info("Dry run: no certificate will be imported")
    logger.info("%s certificates to import by batch of %s", total, batch_size)

    batch_count = 0
    for batch_offset in range(global_offset, global_offset + total, batch_size):
        batch_count += 1
        import_certificates_batch_task.delay(
            batch_offset=batch_offset,
            batch_size=batch_size,
            total=total,
            course_id=course_id,
            dry_run=dry_run,
        )
    logger.info("%s import certificates tasks launched", batch_count)


@app.task(bind=True)
def import_certificates_batch_task(self, **kwargs):
    """
    Task to import certificates from the Open edX database to the Joanie database.
    """
    try:
        report = import_certificates_batch(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    return report


def import_certificates_batch(
    batch_offset, batch_size, total, course_id, dry_run=False
):
    """Batch import certificates from Open edX certificates_generatedcertificate"""
    db = OpenEdxDB()
    report = {
        "certificates": {
            "created": 0,
            "skipped": 0,
            "errors": 0,
        }
    }
    hashids = Hashids(salt=settings.EDX_SECRET)
    certificates = db.get_certificates(batch_offset, batch_size, course_id=course_id)
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

        if models.Certificate.objects.filter(enrollment=enrollment).exists():
            report["certificates"]["skipped"] += 1
            continue

        verification_hash = hashids.encode(edx_certificate.id)

        certificate_context = {
            "verification_hash": verification_hash,
            "signatory": None,
        }

        title_object = enrollment.course_run.course

        organization_code = extract_organization_code(edx_certificate.course_id)
        try:
            organization = models.Organization.objects.get(
                code__iexact=organization_code
            )
        except models.Organization.DoesNotExist:
            report["certificates"]["errors"] += 1
            logger.error(
                "No organization found for %s",
                organization_code,
                extra={
                    "context": {
                        "edx_certificate": vars(edx_certificate),
                        "enrollment": enrollment.to_dict(),
                        "course_run": enrollment.course_run.to_dict(),
                    }
                },
            )
            continue

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
                        "logo": image_to_base64(organization.logo)
                        if organization.logo
                        else None,
                        "representative": None,
                        "signature": None,
                    }
                ],
            }

        certificate_template = CERTIFICATE

        if edx_certificate.mode == OPENEDX_MODE_VERIFIED:
            certificate_template = DEGREE
            signatory = edx_mongodb.get_signature_from_enrollment(
                enrollment.course_run.course.code
            )

            signature = None
            signatory_name = None
            if signatory:
                signature_image_path = signatory.get("signature_image_path")
                if signature_image_path.startswith("/"):
                    signature_image_path = signature_image_path[1:]
                signature_path = download_and_store(signature_image_path)
                signature = (
                    image_to_base64(default_storage.open(signature_path))
                    if signature_path
                    else None
                )
                signatory_name = signatory.get("name")

                certificate_context["signatory"] = signatory

            for language, _ in settings.LANGUAGES:
                if signatory_name:
                    certificate_context[language]["organizations"][0][
                        "representative"
                    ] = signatory_name
                if signature:
                    certificate_context[language]["organizations"][0]["signature"] = (
                        signature
                    )

        certificates_to_create.append(
            models.Certificate(
                certificate_definition=models.CertificateDefinition.objects.filter(
                    template=certificate_template
                )
                .order_by("created_on")
                .first(),
                organization=organization,
                enrollment=enrollment,
                issued_on=make_date_aware(edx_certificate.created_date),
                localized_context=certificate_context,
            )
        )

    import_string = "%s %s/%s : %s certificates created, %s skipped, %s errors"
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
        import_string = "Dry run: " + import_string
        report["certificates"]["created"] += len(certificates_to_create)

    total_processed = (
        batch_offset
        + report["certificates"]["created"]
        + report["certificates"]["skipped"]
        + report["certificates"]["errors"]
    )
    percent = format_percent(total_processed, total)
    logger.info(
        import_string,
        percent,
        total_processed,
        total,
        report["certificates"]["created"],
        report["certificates"]["skipped"],
        report["certificates"]["errors"],
    )

    return import_string % (
        percent,
        total_processed,
        total,
        report["certificates"]["created"],
        report["certificates"]["skipped"],
        report["certificates"]["errors"],
    )
