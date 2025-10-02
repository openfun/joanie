"""Tests for the Order submit for signature API."""

import json
from datetime import timedelta
from http import HTTPStatus

from django.core.cache import cache
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories
from joanie.core.models import CourseState
from joanie.payment.factories import BillingAddressDictFactory
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import BaseAPITestCase


class OrderSubmitForSignatureApiTest(BaseAPITestCase):
    """Test the API of the Order submit for signature endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_submit_for_signature_anonymous(self):
        """
        Anonymous user should not be able to submit for signature an order.
        """
        order = factories.OrderFactory(
            product__contract_definition_order=factories.ContractDefinitionFactory()
        )
        factories.ContractFactory(order=order)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION="Bearer fake",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

        content = response.json()
        self.assertEqual(content["detail"], "Given token not valid for any token type")

    def test_api_order_submit_for_signature_user_is_not_owner_of_the_order_to_be_submit(
        self,
    ):
        """
        When submitting an order to the signature procedure, if the order's owner is not the
        current user, it should raise an error. Only the owner of the order can submit for
        signature his order.
        """
        not_owner_user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        owner = factories.UserFactory(email="johndoe@example.fr")
        factories.UserAddressFactory(owner=owner)
        order = factories.OrderFactory(
            owner=owner,
            state=enums.ORDER_STATE_COMPLETED,
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(not_owner_user.username)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

        content = response.json()
        self.assertEqual(content["detail"], "No Order matches the given query.")

    def test_api_order_submit_for_signature_authenticated_but_order_is_not_to_sign(
        self,
    ):
        """
        Authenticated users should only be able to submit for signature an order that is
        in the state 'to sign'.
        If the order is in another state, it should raise an error.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory(owner=user)
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                if state == enums.ORDER_STATE_TO_OWN:
                    order = factories.OrderGeneratorFactory(state=state)
                else:
                    order = factories.OrderGeneratorFactory(owner=user, state=state)
                token = self.get_user_token(user.username)

                response = self.client.post(
                    f"/api/v1.0/orders/{order.id}/submit_for_signature/",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )
                content = response.json()

                if state in [enums.ORDER_STATE_TO_SIGN, enums.ORDER_STATE_SIGNING]:
                    self.assertStatusCodeEqual(response, HTTPStatus.OK)
                    self.assertIsNotNone(content.get("invitation_link"))
                elif state in [enums.ORDER_STATE_DRAFT, enums.ORDER_STATE_ASSIGNED]:
                    self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
                    self.assertEqual(
                        content[0],
                        "No contract definition attached to the contract's product.",
                    )
                elif state == enums.ORDER_STATE_TO_OWN:
                    self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)
                else:
                    self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
                    self.assertEqual(
                        content[0], "Cannot submit an order that is not to sign."
                    )

    def test_api_order_submit_for_signature_order_without_product_contract_definition(
        self,
    ):
        """
        Authenticated user should not be able to submit for signature an order if it has no
        contract definition set on the product. It should raise an error.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.UserAddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product=factories.ProductFactory(contract_definition_order=None),
        )
        token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)

        content = response.json()
        self.assertEqual(
            content[0], "No contract definition attached to the contract's product."
        )

    def test_api_order_submit_for_signature_authenticated(self):
        """
        Authenticated users should be able to create a contract from an order and get in
        return the invitation url to sign the file.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        target_courses = factories.CourseFactory.create_batch(
            2,
            course_runs=factories.CourseRunFactory.create_batch(
                2, state=CourseState.ONGOING_OPEN
            ),
        )
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__target_courses=target_courses,
        )
        order.init_flow(billing_address=BillingAddressDictFactory())
        token = self.get_user_token(user.username)
        expected_substring_invite_url = "https://dummysignaturebackend.fr/?reference="

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertIsNotNone(order.contract)
        self.assertIsNotNone(order.contract.context)
        self.assertIsNotNone(order.contract.definition_checksum)
        self.assertIsNone(order.contract.student_signed_on)
        self.assertIsNotNone(order.contract.submitted_for_signature_on)

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_url = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_url)

        backend = get_signature_backend()
        backend.confirm_signature(reference=order.contract.signature_backend_reference)
        order.refresh_from_db()
        self.assertIsNotNone(order.contract.student_signed_on)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    )
    def test_api_order_submit_for_signature_contract_be_resubmitted_with_validity_period_passed(
        self,
    ):
        """
        Authenticated user should be able to resubmit the order's contract when he did not sign it
        in time before the expiration of the signature's procedure and the context has not changed.
        The contract will get new values after synchronizing because the previous reference has
        been deleted from the signature provider. It should update the fields :
        'definition_checksum', 'signature_backend_reference' and 'submitted_for_signature_on'.
        In return we must have in the response the invitation link to sign the file.
        """
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_SIGNING,
            contract__submitted_for_signature_on=django_timezone.now()
            - timedelta(days=16),
            contract__signature_backend_reference="wfl_fake_dummy_id_will_be_updated",
            contract__definition_checksum="fake_test_file_hash_will_be_updated",
            contract__context="content",
        )
        contract = order.contract
        token = self.get_user_token(order.owner.username)
        expected_substring_invite_url = "https://dummysignaturebackend.fr/?reference="

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        contract.refresh_from_db()
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertNotEqual(contract.context, "content")
        self.assertIn("fake_dummy_file_hash", contract.definition_checksum)
        self.assertNotEqual(contract.signature_backend_reference, "wfl_fake_dummy_id")

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_link = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_link)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    )
    def test_api_order_submit_for_signature_contract_context_has_changed_and_still_valid_period(
        self,
    ):
        """
        Authenticated user should be able to resubmit a contract if the context of the definition
        has changed overtime since it was first generated. The contract object will get new values
        after synchronizing with the signature provider. We get the invitation link in the
        response in return.
        """
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_SIGNING,
            contract__submitted_for_signature_on=django_timezone.now()
            - timedelta(days=2),
            contract__signature_backend_reference="wfl_fake_dummy_id",
            contract__definition_checksum="fake_test_file_hash",
            contract__context="content",
        )
        contract = order.contract
        token = self.get_user_token(order.owner.username)
        order.contract.definition.body = "a new content"
        expected_substring_invite_url = "https://dummysignaturebackend.fr/?reference="

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_for_signature/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        contract.refresh_from_db()
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertNotEqual(contract.signature_backend_reference, "wfl_dummy_test_id_1")
        self.assertNotEqual(contract.definition_checksum, "fake_test_file_hash")
        self.assertNotEqual(contract.context, "a new content")

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_link = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_link)
