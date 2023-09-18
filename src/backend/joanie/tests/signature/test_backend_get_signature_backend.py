"""get_signature_backend() test suite"""

from django.test import TestCase
from django.test.utils import override_settings

from joanie.signature.backends import get_signature_backend
from joanie.signature.backends.base import BaseSignatureBackend
from joanie.signature.backends.dummy import DummySignatureBackend
from joanie.signature.backends.lex_persona.client import LexPersonaClient


class GetSignatureBackendTestSuite(TestCase):
    """Test suite for the get_signature_backend method."""

    @override_settings(
        JOANIE_SIGNATURE_BACKEND={
            "backend": "joanie.signature.backends.dummy.DummySignatureBackend",
            "configuration": {},
        }
    )
    def test_get_signature_backend_get_backend_dummy(self):
        """
        When JOANIE_SIGNATURE_BACKEND is well configured,
        the dummy signature backend should be returned.
        """
        backend = get_signature_backend()
        self.assertEqual(backend.name, "dummy")
        self.assertIsInstance(backend, DummySignatureBackend)
        self.assertIsInstance(backend, BaseSignatureBackend)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND={
            "backend": "joanie.signature.backends.lex_persona.client.LexPersonaClient",
            "configuration": {
                "base_url": "http://lex_persona.test",
                "consent_page": "cop_test_id",
                "signature_page": "sip_test_id",
                "session_user": "usr_id",
                "token": "test_token",
            },
        }
    )
    def test_get_signature_backend_get_backend_client(self):
        """
        When JOANIE_SIGNATURE_BACKEND is well configured,
        the client signature backend should be returned.
        """
        backend = get_signature_backend()
        self.assertEqual(backend.name, "lex_persona")
        self.assertIsInstance(backend, LexPersonaClient)
        self.assertIsInstance(backend, BaseSignatureBackend)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND={
            "backend": "joanie.signature.backends.base.BaseSignatureBackend",
            "configuration": {},
        }
    )
    def test_get_signature_backend_get_backend_base(self):
        """
        When JOANIE_SIGNATURE_BACKEND is well configured,
        the base signature backend should be returned.
        """
        backend = get_signature_backend()
        self.assertEqual(backend.name, "base")
        self.assertIsInstance(backend, BaseSignatureBackend)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND={
            "backend": "joanie.signature.backends.lex_persona.client.LexPersonaClient",
        }
    )
    def test_get_signature_backend_raises_error(self):
        """
        When configuration settings is misconfigured (missing configuration key),
        ValueError exception should be raised.
        """
        with self.assertRaises(ValueError) as context:
            get_signature_backend()
        self.assertEqual(
            str(context.exception),
            (
                "Cannot instantiate a signature backend. "
                "JOANIE_SIGNATURE_BACKEND configuration seems not valid. Check your settings.py."
            ),
        )

    @override_settings(
        JOANIE_SIGNATURE_BACKEND={
            "backend": "joanie.signature.backends.unknown",
            "configuration": {},
        }
    )
    def test_get_signature_backend_raises_error_when_backend_is_unknown(self):
        """
        When JOANIE_SIGNATURE_BACKEND is unknown, ValueError exception should be raised.
        """
        with self.assertRaises(ValueError) as context:
            get_signature_backend()

        self.assertEqual(
            str(context.exception),
            (
                "Cannot instantiate a signature backend. "
                "JOANIE_SIGNATURE_BACKEND configuration seems not valid. Check your settings.py."
            ),
        )
