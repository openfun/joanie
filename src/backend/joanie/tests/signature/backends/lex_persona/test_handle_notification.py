"""Test suite for the Lex Persona Signature Backend handle_notification"""
import json
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

import responses

from joanie.core import factories
from joanie.signature.backends import get_signature_backend


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
class LexPersonaBackendHandleNotificationTestCase(TestCase):
    """Test suite for Lex Persona Signature provider Backend handle_notification."""

    @responses.activate
    def test_backend_lex_persona_handle_notification_workflowstarted_unsupported_event_type(
        self
    ):
        """
        When an incoming webhook event type is 'workflowStarted', and the event is verified,
        it should raise the exception Handle Notification Failed because we don't track this
        specific event type.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowStarted",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)

        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowStarted",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        responses.add(responses.GET, api_url, json=expected_response_data, status=200)

        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['The notification workflowStarted is not supported.']",
        )

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "GET")

    @responses.activate
    def test_backend_lex_persona_handle_notification_workflowstopped_unsupported_event_type(
        self
    ):
        """
        When an incoming webhook event type is 'workflowStopped', and the event is verified,
        it should raise an exception because we don't track this specific event type.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowStopped",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)

        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowStopped",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        responses.add(responses.GET, api_url, json=expected_response_data, status=200)
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['The notification workflowStopped is not supported.']",
        )

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "GET")

    def test_backend_lex_persona_handle_notification_incoming_request_body_is_an_empty_dictionary(
        self,
    ):
        """
        When an incoming webhook event is an empty dictionary, it should raise Retrieve Key Failed
        because the request body is missing the key 'id' we want to retrieve.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": b"{}",
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        backend = get_signature_backend()

        with self.assertRaises(KeyError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "'Missing the key id to retrieve from the webhook event data'",
        )

    def test_backend_lex_persona_handle_notification_body_is_missing_id_key(self):
        """
        When an incoming webhook event is missing the 'id' key, it should raise
        the exception KeyError because we can't verify the webhook event reference.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        backend = get_signature_backend()

        with self.assertRaises(KeyError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "'Missing the key id to retrieve from the webhook event data'",
        )

    def test_backend_lex_persona_handle_notification_with_malformed_json_body(self):
        """
        When an incoming webhook event has a malformed JSON body, it should raise the exception
        ValidationError.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": "malformed JSON body",
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception), "['The JSON body of the request is malformed']"
        )

    @responses.activate
    def test_backend_lex_persona_handle_notification_verify_webhook_event_failed_to_verify(
        self
    ):
        """
        When an incoming event type is 'workflowFinished', but we can't verify that webhook event
        authenticity and integrity, it should raise ValidationError.
        """
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)
        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "status": 404,
            "error": "Not Found",
            "message": "The specified webhook event can not be found.",
            "requestId": "379a3980-481772",
            "code": "WebhookEventNotFound",
        }

        responses.add(responses.GET, api_url, json=expected_response_data, status=400)
        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['Lex Persona: Unable to verify the webhook event with the signature provider.']",
        )
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, api_url)
        self.assertEqual(
            responses.calls[0].request.headers["Authorization"], "Bearer token_id_fake"
        )
        self.assertEqual(responses.calls[0].request.method, "GET")

    @responses.activate
    def test_backend_lex_persona_handle_notification_workflow_finished_event(self):
        """
        When an incoming event type is 'workflowFinished', and the event has been verified,
        then the contract which has the signature backend reference should get updated
        with a new 'signed_on' date and update the value of 'submitted_for_signature_on' to None.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)

        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowFinished",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        responses.add(responses.GET, api_url, json=expected_response_data, status=200)

        backend = get_signature_backend()

        backend.handle_notification(request)

        contract.refresh_from_db()
        self.assertIsNotNone(contract.signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    )
    @responses.activate
    def test_backend_lex_persona_handle_notification_workflow_finished_event_but_signature_expired(
        self
    ):
        """
        When an incoming event type is 'workflowFinished' and the 'id' has been verified at the
        signature provider, but the expiration date to sign has passed, then we should raise an
        error. The file is eligible for a signature for a period of 15 days.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "workflowFinished",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)

        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "workflowFinished",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        responses.add(responses.GET, api_url, json=expected_response_data, status=200)

        backend = get_signature_backend()

        with self.assertRaises(ValidationError) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "['The contract validity date of expiration has passed.']",
        )
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.signed_on)

    @responses.activate
    def test_backend_lex_persona_handle_notification_recipient_refused_should_reset_contract(
        self
    ):
        """
        When an incoming event type is 'recipientRefused', and the event has been verified,
        then the contract which has the signature backend reference should be reset on the
        fields : 'context', 'submitted_for_signature_on' 'signature_backend_reference' and
        'definition_checksum' to None.
        """
        user = factories.UserFactory(email="johnnydo@example.fr")
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )
        request_data = {
            "method": "POST",
            "path": "https://mocked_joanie_test/api/v1.0/webhook-signature/",
            "_body": json.dumps(
                {
                    "id": "wbe_id_fake",
                    "tenantId": "ten_id_fake",
                    "userId": "usr_id_fake",
                    "webhookId": "wbh_id_fake",
                    "workflowId": "wfl_id_fake",
                    "stepId": "stp_id_fake",
                    "eventType": "recipientRefused",
                    "created": 1693404075146,
                    "updated": 1693404075146,
                }
            ),
            "content_type": "application/json",
        }
        request = HttpRequest()
        request.__dict__.update(request_data)

        api_url = "https://lex_persona.test01.com/api/webhookEvents/wbe_id_fake"
        expected_response_data = {
            "id": "wbe_id_fake",
            "tenantId": "ten_id_fake",
            "userId": "usr_id_fake",
            "webhookId": "wbh_id_fake",
            "workflowId": "wfl_id_fake",
            "stepId": "stp_id_fake",
            "eventType": "recipientRefused",
            "created": 1693404075146,
            "updated": 1693404075146,
        }
        responses.add(responses.GET, api_url, json=expected_response_data, status=200)

        backend = get_signature_backend()

        backend.handle_notification(request)

        contract.refresh_from_db()
        self.assertIsNone(contract.signed_on)
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.signature_backend_reference)
        self.assertIsNone(contract.definition_checksum)
