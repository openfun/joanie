"""Test suite for the LexPersonaClient and BaseSignatureBackend class."""
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from joanie.signature.backends.base import BaseSignatureBackend
from joanie.signature.backends.lex_persona import LexPersonaClient


class SignatureBackendTestCase(TestCase):
    """Test suite for the LexPersonaClient and BaseSignatureBackend class once initialised"""

    @override_settings(
        JOANIE_SIGNATURE_BACKEND={
            "backend": "joanie.signature.backends.base.BaseSignatureBackend",
            "configuration": {
                "base_url": "http://lex_persona.test",
                "consent_page": "cop_test_id",
                "signature_page": "sip_test_id",
                "session_user": "usr_id",
                "token": "test_token",
            },
        }
    )
    def test_signature_client_base_init_configuration(self):
        """
        Parsing the configuration settings for signature to BaseSignatureBackend
        and check over the ventilation of the values through the class attributes.
        """
        backend_base = BaseSignatureBackend(settings.JOANIE_SIGNATURE_BACKEND)
        self.assertEqual(
            backend_base.configuration["base_url"], "http://lex_persona.test"
        )
        self.assertEqual(backend_base.configuration["consent_page"], "cop_test_id")
        self.assertEqual(backend_base.configuration["session_user"], "usr_id")
        self.assertEqual(backend_base.configuration["signature_page"], "sip_test_id")
        self.assertEqual(backend_base.configuration["token"], "test_token")

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
    def test_signature_client_init_configuration(self):
        """
        Parsing the configuration settings for signature to LexPersonaClient
        and check over the ventilation of the values through the class attributes.
        """
        backend_client = LexPersonaClient(settings.JOANIE_SIGNATURE_BACKEND)
        self.assertEqual(backend_client.token, "test_token")
        self.assertEqual(backend_client.signature_page, "sip_test_id")
        self.assertEqual(backend_client.session_user, "usr_id")
        self.assertEqual(backend_client.base_url, "http://lex_persona.test")
        self.assertIsInstance(backend_client, BaseSignatureBackend)

    def test_signature_client_base_signature_backend_init_no_configuration(self):
        """
        With an empty dictionary for instantiating the BaseSignatureBackend class,
        it should return an empty dictionnary.
        """
        backend_base = BaseSignatureBackend({})
        self.assertEqual(backend_base.configuration, {})

    def test_signature_client_init_no_configuration(self):
        """
        With an empty dictionary for instantiating the LexPersonaClient class,
        it should return the attributes default values, which is en empty string.
        """
        backend_client = LexPersonaClient({})
        self.assertEqual(backend_client.token, None)
        self.assertEqual(backend_client.signature_page, None)
        self.assertEqual(backend_client.session_user, None)
        self.assertIsInstance(backend_client, BaseSignatureBackend)
