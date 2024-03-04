"""Signature exceptions"""

from http import HTTPStatus

from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import APIException


class CreateSignatureProcedureFailed(APIException):
    """
    Exception triggered when creating a signature procedure failed.
    This exception is raised when attempting to create a signature procedure due to missing
    required data in the payload's creation
    """

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot create a signature procedure.")
    default_code = "create_signature_procedure_failed"


class UploadFileFailed(APIException):
    """Exception triggered when uploading a file at the signature provider failed."""

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _(
        "Cannot upload the file to the signature provider with the signature reference."
    )
    default_code = "upload_file_failed"


class StartSignatureProcedureFailed(APIException):
    """
    Exception triggered when starting the signature procedure failed.
    This exception is raised when attempting to start a workflow that does not exists, or
    that is already finished.
    """

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _(
        "Cannot start the signature procedure with the signature reference."
    )
    default_code = "start_signature_procedure_failed"


class InvitationSignatureFailed(APIException):
    """
    Exception triggered when getting the signature invitation link failed.
    This exception is raised if the signer's email is not registered to sign a file, or if
    the signature backend reference does not exist.
    """

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _(
        "Cannot get invitation link to sign the file from the signature provider."
    )
    default_code = "get_invitation_signature_failed"


class DeleteSignatureProcedureFailed(APIException):
    """
    Exception triggered when deleting a signature procedure at the signature provider failed.
    This exception is raised when attempting to delete a signature procedure that
    does not exists at the signature provider.
    """

    status_code = HTTPStatus.BAD_REQUEST
    default_detail = _("Cannot delete the signature procedure.")
    default_code = "delete_signature_procedure_failed"
