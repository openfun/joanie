"""Tests for the Order submit for signature API."""
import json
import random
from datetime import timedelta
from http import HTTPStatus

from django.core.cache import cache
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone as django_timezone

from joanie.core import enums, factories
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
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        factories.ContractFactory(order=order)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION="Bearer fake",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(not_owner_user.username)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        content = response.json()
        self.assertEqual(content["detail"], "Not found.")

    def test_api_order_submit_for_signature_authenticated_but_order_is_not_validate(
        self,
    ):
        """
        Authenticated users should not be able to submit for signature an order that is
        not state equal to 'validated'.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.UserAddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=random.choice(
                [
                    enums.ORDER_STATE_CANCELED,
                    enums.ORDER_STATE_PENDING,
                    enums.ORDER_STATE_SUBMITTED,
                    enums.ORDER_STATE_DRAFT,
                ]
            ),
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        token = self.get_user_token(user.username)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        content = response.json()
        self.assertEqual(
            content[0], "Cannot submit an order that is not yet validated."
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
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(contract_definition=None),
        )
        token = self.get_user_token(user.username)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

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
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        token = self.get_user_token(user.username)
        expected_substring_invite_url = (
            "https://dummysignaturebackend.fr/?requestToken="
        )
        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNotNone(order.contract)
        self.assertIsNotNone(order.contract.context)
        self.assertIsNotNone(order.contract.definition_checksum)
        self.assertIsNotNone(order.contract.student_signed_on)
        self.assertIsNotNone(order.contract.submitted_for_signature_on)

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_url = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_url)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
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
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        token = self.get_user_token(user.username)
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id_will_be_updated",
            definition_checksum="fake_test_file_hash_will_be_updated",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )
        expected_substring_invite_url = (
            "https://dummysignaturebackend.fr/?requestToken="
        )

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        contract.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(contract.context, "content")
        self.assertIn("fake_dummy_file_hash", contract.definition_checksum)
        self.assertNotEqual(contract.signature_backend_reference, "wfl_fake_dummy_id")

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_link = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_link)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
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
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        token = self.get_user_token(user.username)
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=2),
        )
        contract.definition.body = "a new content"
        expected_substring_invite_url = (
            "https://dummysignaturebackend.fr/?requestToken="
        )

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        contract.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(contract.signature_backend_reference, "wfl_dummy_test_id_1")
        self.assertNotEqual(contract.definition_checksum, "fake_test_file_hash")
        self.assertNotEqual(contract.context, "a new content")

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_link = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_link)
