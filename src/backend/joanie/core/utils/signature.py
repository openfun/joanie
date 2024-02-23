"""
Module to check the signature of a request.
"""
import hashlib
import hmac

from django.conf import settings

from rest_framework import exceptions


def check_signature(request, settings_name):
    """Check the signature of a request."""
    msg = request.body.decode("utf-8")
    # Check if the provided signature is valid against any secret in our list
    #
    # We need to do this to support 2 or more versions of our infrastructure at the same time.
    # It then enables us to do updates and change the secret without incurring downtime.
    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        raise exceptions.PermissionDenied("Missing authentication.")
    signature_is_valid = any(
        authorization_header
        == "SIG-HMAC-SHA256 {:s}".format(  # pylint: disable = consider-using-f-string
            hmac.new(
                secret.encode("utf-8"),
                msg=msg.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
        )
        for secret in getattr(settings, settings_name, [])
    )
    if not signature_is_valid:
        raise exceptions.AuthenticationFailed("Invalid authentication.")
