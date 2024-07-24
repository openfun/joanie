"""Celery tasks for importing Open edX certificates to Joanie organizations."""

import re

# pylint: disable=too-many-locals,too-many-statements,too-many-branches,broad-exception-caught
# ruff: noqa: SLF001,PLR0915,PLR0912,BLE001
from logging import getLogger

from django.conf import settings

from hashids import Hashids

from joanie.celery_app import app
from joanie.core import enums, models
from joanie.core.enums import CERTIFICATE, DEGREE
from joanie.core.models import Certificate, DocumentImage
from joanie.core.utils import file_checksum
from joanie.edx_imports import edx_mongodb
from joanie.edx_imports.edx_database import OpenEdxDB
from joanie.edx_imports.utils import (
    download_signature_image,
    extract_organization_code,
    format_percent,
    make_date_aware,
    set_certificate_images,
    update_context_signatory,
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
                    extra={
                        "context": {
                            "edx_certificate": edx_certificate.safe_dict(),
                            "edx_user": edx_certificate.user.safe_dict(),
                        }
                    },
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
                            "edx_certificate": edx_certificate.safe_dict(),
                            "enrollment": enrollment.to_dict(),
                            "course_run": enrollment.course_run.to_dict(),
                        }
                    },
                )
                continue

            logo = None
            if organization.logo:
                logo_checksum = file_checksum(organization.logo)
                (logo, _created) = DocumentImage.objects.get_or_create(
                    checksum=logo_checksum,
                    defaults={"file": organization.logo},
                )

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
                            "logo_id": logo.id if logo else None,
                            "signature_id": None,
                            "representative": None,
                            "representative_profession": None,
                        }
                    ],
                }

            certificate_template = CERTIFICATE

            if edx_certificate.mode == OPENEDX_MODE_VERIFIED:
                certificate_template = DEGREE
                signatory = edx_mongodb.get_signatory_from_course_id(
                    edx_certificate.course_id
                )

                if signatory:
                    signature_image_path = signatory.get("signature_image_path")
                    signature, _ = download_signature_image(signature_image_path)
                    if signature:
                        signatory["signature_id"] = str(signature.id)
                    certificate_context["signatory"] = signatory

                    certificate_context = update_context_signatory(
                        certificate_context, signatory
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
        except Exception as e:
            report["certificates"]["errors"] += 1
            logger.error(
                "Error creating Certificate: %s",
                e,
                extra={
                    "context": {
                        "exception": e,
                        "edx_certificate": edx_certificate.safe_dict(),
                    }
                },
            )
            continue

    import_string = "%s %s/%s : %s certificates created, %s skipped, %s errors"
    if not dry_run:
        certificate_issued_on_field = models.Certificate._meta.get_field("issued_on")
        certificate_issued_on_field.auto_now = False
        certificate_issued_on_field.editable = True

        certificates_created = models.Certificate.objects.bulk_create(
            certificates_to_create
        )
        # Create the relation between the certificate and the document images
        for certificate in certificates_created:
            set_certificate_images(certificate)

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


@app.task(bind=True)
def populate_signatory_certificates_task(self, **kwargs):
    """Task to populate signatory certificates for those this information is missing."""
    try:
        report = populate_signatory_certificates(**kwargs)
    except Exception as e:
        logger.exception(e)
        raise self.retry(exc=e) from e
    return report


def populate_signatory_certificates(certificate_id=None, course_id=None):
    """
    Retrieve existing certificates without signatory and populate them with the signatory
    First try to retrieve signatory information from OpenEdX instance otherwise
    use the organization signatory information.
    """
    report = {
        "total": 0,
        "populated": 0,
        "errors": 0,
        "skipped": 0,
    }

    queryset = {
        "certificate_definition__template": enums.DEGREE,
        "enrollment__isnull": False,
    }
    if certificate_id:
        queryset["id"] = certificate_id
    if course_id:
        queryset["enrollment__course_run__resource_link__icontains"] = course_id

    certificates = Certificate.objects.filter(**queryset).select_related("organization")

    report["total"] = certificates.count()

    for certificate in certificates.iterator():
        localized_context = certificate.localized_context.copy()
        resource_link = certificate.enrollment.course_run.resource_link
        key = course_id or (
            re.match("^.*/courses/(?P<course_id>.*)/course/?$", resource_link).group(
                "course_id"
            )
        )

        if not key:
            report["errors"] += 1
            continue

        try:
            organization = certificate.localized_context.get(
                settings.LANGUAGE_CODE
            ).get("organizations")[0]
        except (AttributeError, TypeError, IndexError):
            report["errors"] += 1
            continue

        if organization.get("signature_id") is not None and organization.get(
            "representative"
        ):
            report["skipped"] += 1
            continue

        if signatory := edx_mongodb.get_signatory_from_course_id(key):
            signature_image_path = signatory.get("signature_image_path")
            signature, _ = download_signature_image(signature_image_path)
            if signature:
                signatory["signature_id"] = str(signature.id)
            localized_context["signatory"] = signatory
        else:
            organization = certificate.organization
            signature_checksum = file_checksum(organization.signature)
            signature, _ = DocumentImage.objects.get_or_create(
                checksum=signature_checksum,
                defaults={"file": organization.signature},
            )
            signatory = {
                "name": organization.signatory_representative
                or organization.representative,
                "title": organization.signatory_representative_profession
                if organization.signatory_representative
                else organization.representative_profession,
                "signature_id": str(signature.id) if signature else None,
            }

        if not signatory.get("name") or not signatory.get("signature_id"):
            report["errors"] += 1
            continue

        certificate.localized_context = update_context_signatory(
            localized_context, signatory
        )
        certificate.save()
        report["populated"] += 1

    report_string = "%s certificates processed, %s populated, %s skipped, %s errors"
    logger.info(
        report_string,
        report["total"],
        report["populated"],
        report["skipped"],
        report["errors"],
    )

    return report_string % (
        report["total"],
        report["populated"],
        report["skipped"],
        report["errors"],
    )
