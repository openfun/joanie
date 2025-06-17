"""Utility to generate a ZIP archive of PDF bytes files for contracts that are signed"""

import io
import zipfile
from logging import getLogger
from typing import List
from uuid import uuid4

from django.core.files.storage import storages
from django.db.models import Q

from joanie.core import enums
from joanie.core.models import BatchOrder, Contract, Order, OrganizationAccess
from joanie.signature.backends import get_signature_backend

logger = getLogger(__name__)


def _get_base_signature_backend_references(
    offer=None, organization=None, extra_filters=None
):
    """
    Build the base query to get signature backend references from an Offer
    object or an Organization object when the contract is signed. You can pass both parameters if
    you need to filter out by organization when the offer is shared between
    many organizations.

    You may use an additional parameter `extra_filters` if you need to filter out even more the
    base queryset of the Contract (check if the user has access to the organization for example).
    """
    if not extra_filters:
        extra_filters = {}

    base_query = (
        Contract.objects.filter(
            student_signed_on__isnull=False,
            organization_signed_on__isnull=False,
            **extra_filters,
        )
        .exclude(order__state=enums.ORDER_STATE_CANCELED)
        .select_related("order")
    )

    if offer:
        base_query = base_query.filter(
            Q(order__course_id=offer.course_id)
            | Q(order__enrollment__course_run__course_id=offer.course_id),
            order__product_id=offer.product_id,
        )

    if organization:
        base_query = base_query.filter(order__organization_id=organization.pk)

    return base_query


def get_signature_backend_references_exists(
    offer=None, organization=None, extra_filters=None
):
    """
    Check if signature backend references exist from either an Offer
    object or an Organization object when the contract is signed.

    You may use an additional parameter `extra_filters` if you need to filter out even more the
    base queryset of the Contract (check if the user has access to the organization for example).
    """
    base_query = _get_base_signature_backend_references(
        offer=offer,
        organization=organization,
        extra_filters=extra_filters,
    )

    return base_query.distinct().exists()


def get_signature_backend_references(offer=None, organization=None, extra_filters=None):
    """
    Get a generator object with signature backend references from either an Offer
    object or an Organization object when the contract is signed. Otherwise, it returns an empty
    generator if there are no signed contracts yet.

    You may use an additional parameter `extra_filters` if you need to filter out even more the
    base queryset of the Contract (check if the user has access to the organization for example).

    We use the iterator method because it reduces memory consumption and improve the performance
    when we work with large dataset. It processes the database records one at a time instead of
    loading the entire QuerySet into memory all at once.
    """
    base_query = _get_base_signature_backend_references(
        offer=offer,
        organization=organization,
        extra_filters=extra_filters,
    )

    signature_backend_references = (
        base_query.values_list("signature_backend_reference", flat=True)
        .order_by("signature_backend_reference")
        .distinct()
        .iterator()
    )

    return signature_backend_references


def get_pdf_bytes_of_contracts(signature_backend_references: list) -> list:
    """
    Get PDF bytes files from a list of signature backend references at the signature provider.
    It returns an empty list if the input parameter has no item in its list.
    """
    signature_backend = get_signature_backend()

    return [
        signature_backend.get_signed_file(reference_id)
        for reference_id in signature_backend_references
    ]


def generate_zip_archive(pdf_bytes_list: list, user_uuid: str, zip_uuid=None) -> str:
    """
    Generate a ZIP archive from a list of PDF bytes and save it in the File System Storage.
    Once it has been generated, we return the filename of the ZIP archive stored.

    The filename will be build the following way : `{user_id}/{uuid}.zip`. The filename can be used
    to fetch it from the file system storage.

    The selected compression method `zipfile.ZIP_DEFLATED`. It is efficient in terms of compression
    and decompression, making it a good choice for general-purpose compression.
    """
    if not pdf_bytes_list:
        error_message = (
            "You should provide a non-empty list of PDF bytes to generate ZIP archive."
        )
        logger.error(error_message)
        raise ValueError(error_message)

    # Create the ZIP Archive.
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(
        file=zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zipf:
        for index, pdf_bytes in enumerate(pdf_bytes_list):
            pdf_filename = f"contract_{index}.pdf"
            # Add PDF bytes file in ZIP archive.
            zipf.writestr(pdf_filename, pdf_bytes)
        zipf.close()

    zip_uuid = zip_uuid if zip_uuid else uuid4()
    zip_archive_name = f"{user_uuid}_{zip_uuid}.zip"
    zip_buffer.seek(0)

    storage = storages["contracts"]
    storage.save(name=zip_archive_name, content=zip_buffer)

    return zip_archive_name


def order_has_organization_owner(order: Order | BatchOrder) -> bool:
    """
    Returns True whether we can find at least one organization owner
    with the appropriate access rights, otherwise we return False.
    """
    return OrganizationAccess.objects.filter(
        organization=order.organization, role=enums.OWNER
    ).exists()


def get_signature_references(organization_id: str, student_has_not_signed: bool):
    """
    Get all contracts that are not fully signed and attached to the organization.
    The parameter `student_has_not_signed` when set to `True` means the contracts
    are not yet signed at all, otherwise, it means that there is already a student's
    signature.
    """
    return (
        Contract.objects.filter(
            submitted_for_signature_on__isnull=False,
            order__organization_id=organization_id,
            organization_signed_on__isnull=True,
            student_signed_on__isnull=student_has_not_signed,
        )
        .exclude(order__state=enums.ORDER_STATE_CANCELED)
        .values_list("signature_backend_reference", flat=True)
        .distinct()
        .iterator()
    )


def _update_signatories(
    signature_backend, reference_ids: List[str], all_signatories: bool
):
    """
    Update signatories on signature procedures from a list of contract references ids
    with the signature provider. It returns the references that were udpated.
    """
    return [
        signature_backend.update_signatories(
            reference_id=reference_id, all_signatories=all_signatories
        )
        for reference_id in reference_ids
    ]


def update_signatories_for_contracts(organization_id: str):
    """
    Updates ongoing signature procedures attached to the organization by adding new
    signatories. It returns the signature backend references that were successfully updated in
    each category (update all signatories and update organization signatories).
    """
    organization_signatories_references = get_signature_references(
        organization_id=organization_id, student_has_not_signed=False
    )
    all_signatories_references = get_signature_references(
        organization_id=organization_id, student_has_not_signed=True
    )

    signature_backend = get_signature_backend()

    organization_signatories_references_updated = _update_signatories(
        signature_backend=signature_backend,
        reference_ids=organization_signatories_references,
        all_signatories=False,
    )

    all_signatories_references_updated = _update_signatories(
        signature_backend=signature_backend,
        reference_ids=all_signatories_references,
        all_signatories=True,
    )

    return {
        "organization_signatories_updated": organization_signatories_references_updated,
        "all_signatories_updated": all_signatories_references_updated,
    }
