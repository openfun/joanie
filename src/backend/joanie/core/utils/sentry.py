"""Sentry utilities."""

import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

from cryptography.fernet import Fernet, InvalidToken

RAW_KEYS = ["application", "sys.argv"]


class SentryEncoder(DjangoJSONEncoder):
    """
    A JSON encoder for sentry context.
    """

    def default(self, o):
        if o.__class__.__name__ in ["ImageFieldFile", "ThumbnailerImageFieldFile"]:
            return o.path
        if o.__class__.__name__ == "Country":
            return o.name
        if o.__class__.__name__ == "Site":
            return o.domain
        if o.__class__.__name__ == "Decimal" or isinstance(o, Exception):
            return str(o)
        if o.__class__.__name__ == "Money":
            return str(o.amount)

        return super().default(o)


def before_send(event, hint):  # pylint: disable=unused-argument
    """Encrypt the additional data of the event sent to Sentry."""
    if extra := event.get("extra"):
        event["extra"] = encrypt_extra(extra)
    if breadcrumbs := event.get("breadcrumbs"):
        for breadcrumb in breadcrumbs.get("values", []):
            if data := breadcrumb.get("data"):
                breadcrumb["data"] = encrypt_extra(data)
    return event


def encrypt_extra(extra):
    """
    Encrypt extra data.

    Except for the keys in RAW_KEYS, encrypt the extra data at the key "encrypted_context".
    """
    key = settings.LOGGING_SECRET_KEY
    if not key:
        return extra

    to_encrypt = {}
    encrypted_extra = {}
    for key, value in extra.items():
        if key in RAW_KEYS:
            encrypted_extra[key] = value
        else:
            to_encrypt.update({key: value})
    if to_encrypt:
        encrypted_extra["encrypted_context"] = encrypt_data(to_encrypt)
    return encrypted_extra


def serialize_data(data):
    """Serialize data."""
    return json.dumps(data, cls=SentryEncoder).encode()


def encrypt_data(data):
    """Encrypt data."""
    key = settings.LOGGING_SECRET_KEY
    if not key:
        return data

    try:
        data = serialize_data(data)
    except TypeError:
        return data

    try:
        cipher_suite = Fernet(key)
    except ValueError:
        return {"error": "Log context encryption failed. The secret key is invalid."}

    cipher_text = cipher_suite.encrypt(data)
    return cipher_text.decode()


def decrypt_data(encrypted_data):
    """Decrypt data."""
    key = settings.LOGGING_SECRET_KEY

    try:
        cipher_suite = Fernet(key)
        plain_text = cipher_suite.decrypt(encrypted_data)
        decrypted_data = json.loads(plain_text.decode())
    except (json.JSONDecodeError, InvalidToken) as e:
        decrypted_data = str(e)

    return decrypted_data
