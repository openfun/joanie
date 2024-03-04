"""get_signature_backend() test suite"""

from django.test import TestCase
from django.test.utils import override_settings

from joanie.signature.backends import get_signature_backend
from joanie.signature.backends.base import BaseSignatureBackend


class GetSignatureBackendTestSuite(TestCase):
    """Test suite for the get_signature_backend method."""

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.base.BaseSignatureBackend"
    )
    def test_backend_get_signature_get_backend_base(self):
        """
        When JOANIE_SIGNATURE_BACKEND is well configured in settings, the base signature backend
        is returned when calling the method `get_signature_backend`
        """

        backend = get_signature_backend()

        self.assertEqual(backend.name, "base")
        self.assertIsInstance(backend, BaseSignatureBackend)
        self.assertEqual(backend.required_settings, [])

    def test_backend_get_signature_get_backend_dummy(self):
        """
        When JOANIE_SIGNATURE_BACKEND is well configured in settings, the dummy signature backend
        is returned when calling the method `get_signature_backend`
        """

        backend = get_signature_backend()

        self.assertEqual(backend.name, "dummy")
        self.assertIsInstance(backend, BaseSignatureBackend)
        self.assertEqual(backend.required_settings, [])

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend"
    )
    def test_backend_get_signature_get_backend_lex_persona(self):
        """
        When JOANIE_SIGNATURE_BACKEND is well configured in settings, lex persona signature backend
        is returned when calling the method `get_signature_backend`
        """
        required_settings = [
            "BASE_URL",
            "CONSENT_PAGE_ID",
            "SESSION_USER_ID",
            "PROFILE_ID",
            "TOKEN",
        ]

        backend = get_signature_backend()

        self.assertEqual(backend.name, "lex_persona")
        self.assertIsInstance(backend, BaseSignatureBackend)
        self.assertEqual(backend.required_settings, required_settings)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.UnknownsignatureBackend"
    )
    def test_backend_get_signature_get_backend_unknown_class_raises_import_error(
        self,
    ):
        """
        When JOANIE_SIGNATURE_BACKEND is improperly configured with a module that does not
        exist, it must raise an import error.
        """
        with self.assertRaises(ImportError) as context:
            get_signature_backend()

        self.assertEqual(
            str(context.exception),
            'Module "joanie.signature.backends" does not'
            ' define a "UnknownsignatureBackend" attribute/class',
        )

    @override_settings(JOANIE_SIGNATURE_BACKEND="joanie.signature.backends")
    def test_backend_get_signature_get_backend_unknown_module_raises_type_error(
        self,
    ):
        """
        When JOANIE_SIGNATURE_BACKEND is improperly configured that is pointing to a folder,
        it must raise a TypeError.
        """
        with self.assertRaises(TypeError) as context:
            get_signature_backend()

        self.assertEqual(str(context.exception), "'module' object is not callable")
