"""Test suite for the Lex Persona Signature Backend with mocking responses"""
# pylint: disable=too-many-public-methods, too-many-lines, protected-access
import json
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

import responses

from joanie.core import factories
from joanie.signature import exceptions
from joanie.signature.backends import get_signature_backend
from joanie.signature.backends.lex_persona import LexPersonaBackend


@override_settings(
    JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.lex_persona.LexPersonaBackend",
    JOANIE_SIGNATURE_LEXPERSONA_BASE_URL="https://lex_persona.test01.com",
    JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID="cop_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID="usr_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID="sip_profile_id_fake",
    JOANIE_SIGNATURE_LEXPERSONA_TOKEN="token_id_fake",
    JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    JOANIE_SIGNATURE_TIMEOUT=3,
)
class LexPersonaBackendTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend."""

    def test_backend_lex_persona_prepare_recipient_information_of_the_signer(self):
        """
        When we prepare the payload to create a signature procedure, it should
        return a list with a dictionnary of the owner's information.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        factories.AddressFactory.create(owner=user)
        order = factories.OrderFactory(owner=user)
        country = order.owner.addresses.filter(is_main=True).first().country.code
        backend = get_signature_backend()
        expected_prepared_recipient_data = [
            {
                "email": order.owner.email,
                "firstName": order.owner.first_name,
                "lastName": ".",
                "country": country.upper(),
                "preferred_locale": order.owner.language.lower(),
                "consentPageId": "cop_id_fake",
            }
        ]

        recipient_data = backend._prepare_recipient_information_of_the_signer(order)

        self.assertEqual(recipient_data, expected_prepared_recipient_data)
 
