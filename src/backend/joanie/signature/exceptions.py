"""Signature exceptions"""
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import APIException


class DownloadFileError(APIException):
    """Exception triggered when the document cannot be download."""

    status_code = 400
    default_detail = _("Can not download document, please check your workflow id")
    default_code = "download_file_error"
