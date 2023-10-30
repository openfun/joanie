"""Utility to generate a zipfile of PDF bytes files for contracts that are signed"""
import io
import zipfile
from logging import getLogger

from django.core.files.storage import default_storage
from django.db.models import Q

from joanie.core import enums, models
from joanie.signature.backends import get_signature_backend

logger = getLogger(__name__)


def get_signature_backend_references(
    course_product_relation: models.CourseProductRelation,
) -> list:
    """
    Get a list of signature backend references from a course product relation object that are
    attached to a validated orders if it exists, else it returns an empty string.
    """
    signature_backend_references = (
        models.Order.objects.filter(
            Q(course_id=course_product_relation.course.pk)
            | Q(product_id=course_product_relation.product.pk),
            contract__signed_on__isnull=False,
            state=enums.ORDER_STATE_VALIDATED,
        )
        .select_related("contract")
        .values_list("contract__signature_backend_reference", flat=True)
        .order_by("contract__signature_backend_reference")
    )
    return list(signature_backend_references)


def fetch_pdf_bytes_of_contracts(signature_backend_references: list) -> list:
    """
    Retrieve PDF bytes files from a list of signature backend reference at the signature provider.
    """
    signature_backend = get_signature_backend()

    pdf_bytes_collection = [
        signature_backend.get_signed_file(reference_id)
        for reference_id in signature_backend_references
    ]

    return pdf_bytes_collection


def generate_zipfile(pdf_bytes_list: list) -> str:
    """
    Generate a zipfile from a list of PDF bytes and save the ZIP archive in
    default storage. The method returns the filename of the ZIP archive once done. This filename
    can be used to retrieve it from default storage.

    Used compression method `zipfile.ZIP_DEFLATED`, It is efficient in terms of compression and
    decompression, making it a good choice for general-purpose compression.
    """
    if not pdf_bytes_list:
        logger.error(
            "You need to provide a list of PDF bytes to generate a ZIP archive."
            "Your actual list is empty : %s",
            pdf_bytes_list,
        )
        raise ValueError(
            "You need to provide a non-empty list of PDF bytes to generate a ZIP archive."
        )

    zip_buffer = io.BytesIO()  # Create the ZIP Archive.
    with zipfile.ZipFile(
        file=zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zipf:
        for index, pdf_bytes in enumerate(pdf_bytes_list):
            pdf_filename = f"contract_{index}.pdf"
            zipf.writestr(pdf_filename, pdf_bytes)  # Add PDF bytes file in ZIP archive.

    zip_file_name = "signed_contracts_extract.zip"
    zip_buffer.seek(0)
    default_storage.save(name=zip_file_name, content=zip_buffer)

    return zip_file_name
