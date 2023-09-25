"""Test suite of the method ready() for Signature AppConfig"""
import random

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings


class AppSignatureConfigTestCase(TestCase):
    """
    Test suite to control if all required settings exist depending on the signature
    backend. Knowing, that a signature provider is not required, but if one is set it should be
    well configured with all required setting awaited.
    """

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
        JOANIE_SIGNATURE_LEXPERSONA_BASE_URL=None,
        JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID="fake_cop_id",
        JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID="fake_user_id",
        JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID="fake_profile_id",
        JOANIE_SIGNATURE_LEXPERSONA_TOKEN="fake_token_id",
    )
    def test_ready_method_with_a_required_configuration_setting_is_not_defined(
        self,
    ):
        """
        Test the scenario where a required configuration is not defined (has None value) in
        settings. We want to verify that the `ready` method raises an improperly configured error.
        """
        signature_app_config = apps.get_app_config("signature")

        with self.assertRaises(ImproperlyConfigured) as context:
            signature_app_config.ready()

        self.assertEqual(
            str(context.exception),
            "Required setting JOANIE_SIGNATURE_LEXPERSONA_BASE_URL is not defined.",
        )

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
        JOANIE_SIGNATURE_LEXPERSONA_BASE_URL="https://fake-base-url.test",
        JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID="fake_cop_id",
        JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID="fake_user_id",
        JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID="fake_profile_id",
        JOANIE_SIGNATURE_LEXPERSONA_TOKEN="fake_token_id",
    )
    def test_ready_method_with_all_required_setting_defined_for_the_api_class(self):
        """
        Test the scenario where required settings are all well defined for the signature backend.
        We verify that the `ready` method does not raise any errors.
        """
        signature_app_config = apps.get_app_config("signature")
        signature_app_config.ready()

        verbose_name = signature_app_config.verbose_name
        name = signature_app_config.name

        self.assertEqual(verbose_name, "Joanie signature application")
        self.assertEqual(name, "joanie.signature")

    @override_settings(
        JOANIE_SIGNATURE_BACKEND=random.choice(
            [
                "joanie.signature.backends.dummy.DummySignatureBackend",
                "joanie.signature.backends.base.BaseSignatureBackend",
            ]
        )
    )
    def test_ready_method_with_no_required_setting_needed_for_base_and_dummy(self):
        """
        Test the scenario where the 'dummy' and the 'base' signature backend do not require
        any specific configuration keys except for the 'JOANIE_SIGNATURE_BACKEND' configuration.
        """
        signature_app_config = apps.get_app_config("signature")
        signature_app_config.ready()

        verbose_name = signature_app_config.verbose_name
        name = signature_app_config.name

        self.assertEqual(verbose_name, "Joanie signature application")
        self.assertEqual(name, "joanie.signature")
