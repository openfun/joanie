"""
Test suite for organization models
"""
import uuid

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone

import factory

from joanie.core import enums, factories, models
from joanie.core.exceptions import NoContractToSignError
from joanie.tests.base import BaseAPITestCase


class OrganizationModelsTestCase(BaseAPITestCase):
    """Test suite for the Organization model."""

    def test_models_organization_fields_code_normalize(self):
        """The `code` field should be normalized to an ascii slug on save."""
        organization = factories.OrganizationFactory()

        organization.code = "Là&ça boô"
        organization.save()
        self.assertEqual(organization.code, "LACA-BOO")

    def test_models_organization_fields_code_unique(self):
        """The `code` field should be unique among organizations."""
        factories.OrganizationFactory(code="the-unique-code")

        # Creating a second organization with the same code should raise an error...
        with self.assertRaises(ValidationError) as context:
            factories.OrganizationFactory(code="the-unique-code")

        self.assertEqual(
            context.exception.messages[0], "Organization with this Code already exists."
        )
        self.assertEqual(
            models.Organization.objects.filter(code="THE-UNIQUE-CODE").count(), 1
        )

    # get_abilities

    def test_models_organization_get_abilities_anonymous(self):
        """Check abilities returned for an anonymous user."""
        organization = factories.OrganizationFactory()
        abilities = organization.get_abilities(AnonymousUser())

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_organization_get_abilities_authenticated(self):
        """Check abilities returned for an authenticated user."""
        organization = factories.OrganizationFactory()
        abilities = organization.get_abilities(factories.UserFactory())
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_organization_get_abilities_owner(self):
        """Check abilities returned for the owner of a organization."""
        access = factories.UserOrganizationAccessFactory(role="owner")
        abilities = access.organization.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": True,
                "get": True,
                "patch": True,
                "put": True,
                "manage_accesses": True,
            },
        )

    def test_models_organization_get_abilities_administrator(self):
        """Check abilities returned for the administrator of a organization."""
        access = factories.UserOrganizationAccessFactory(role="administrator")
        abilities = access.organization.get_abilities(access.user)
        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": True,
                "put": True,
                "manage_accesses": True,
            },
        )

    def test_models_organization_get_abilities_member_user(self):
        """Check abilities returned for the member of a organization."""
        access = factories.UserOrganizationAccessFactory(role="member")

        with self.assertNumQueries(1):
            abilities = access.organization.get_abilities(access.user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_organization_get_abilities_preset_role(self):
        """No query is done if the role is preset e.g. with query annotation."""
        access = factories.UserOrganizationAccessFactory(role="member")
        access.organization.user_role = "member"

        with self.assertNumQueries(0):
            abilities = access.organization.get_abilities(access.user)

        self.assertEqual(
            abilities,
            {
                "delete": False,
                "get": True,
                "patch": False,
                "put": False,
                "manage_accesses": False,
            },
        )

    def test_models_organization_signature_backend_references_to_sign(self):
        """Should return a list of references to sign."""
        now = timezone.now()
        organization = factories.OrganizationFactory()
        relations = factories.CourseProductRelationFactory.create_batch(
            3,
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contracts_to_sign = []
        other_contracts = []
        signed_contracts = []
        for relation in relations:
            contracts_to_sign.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=factory.Sequence(
                        lambda n: f"wfl_fake_dummy_id_{n!s}"
                    ),
                    submitted_for_signature_on=now,
                    student_signed_on=now,
                )
            )
            other_contracts.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=None,
                    submitted_for_signature_on=None,
                    student_signed_on=None,
                )
            )
            signed_contracts.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=factory.Sequence(
                        lambda n: f"wfl_fake_dummy_id_{n!s}"
                    ),
                    submitted_for_signature_on=None,
                    student_signed_on=now,
                    organization_signed_on=now,
                )
            )

        self.assertEqual(
            organization.signature_backend_references_to_sign(),
            [
                contract.signature_backend_reference
                for contract in reversed(contracts_to_sign)
            ],
        )

    def test_models_organization_signature_backend_references_to_sign_specified_ids(
        self,
    ):
        """Should return a list of references to sign for specified contract ids."""
        now = timezone.now()
        organization = factories.OrganizationFactory()
        relations = factories.CourseProductRelationFactory.create_batch(
            3,
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contracts_to_sign = []
        other_contracts = []
        signed_contracts = []
        for relation in relations:
            contracts_to_sign.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=factory.Sequence(
                        lambda n: f"wfl_fake_dummy_id_{n!s}"
                    ),
                    submitted_for_signature_on=now,
                    student_signed_on=now,
                )
            )
            other_contracts.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=None,
                    submitted_for_signature_on=None,
                    student_signed_on=None,
                )
            )
            signed_contracts.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=factory.Sequence(
                        lambda n: f"wfl_fake_dummy_id_{n!s}"
                    ),
                    submitted_for_signature_on=None,
                    student_signed_on=now,
                    organization_signed_on=now,
                )
            )

        contracts_to_sign = contracts_to_sign[:2]
        contracts_to_sign_ids = [contract.id for contract in contracts_to_sign]

        self.assertEqual(
            organization.signature_backend_references_to_sign(
                contracts_ids=contracts_to_sign_ids
            ),
            [
                contract.signature_backend_reference
                for contract in reversed(contracts_to_sign)
            ],
        )

    def test_models_organization_signature_backend_references_to_sign_unknown_specified_ids(
        self,
    ):
        """Should raise an error if a specified contract id does not exist."""
        now = timezone.now()
        organization = factories.OrganizationFactory()
        relations = factories.CourseProductRelationFactory.create_batch(
            3,
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contracts_to_sign = []
        other_contracts = []
        signed_contracts = []
        for relation in relations:
            contracts_to_sign.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=factory.Sequence(
                        lambda n: f"wfl_fake_dummy_id_{n!s}"
                    ),
                    submitted_for_signature_on=now,
                    student_signed_on=now,
                )
            )
            other_contracts.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=None,
                    submitted_for_signature_on=None,
                    student_signed_on=None,
                )
            )
            signed_contracts.append(
                factories.ContractFactory(
                    order__state=enums.ORDER_STATE_VALIDATED,
                    order__product=relation.product,
                    order__course=relation.course,
                    order__organization=organization,
                    signature_backend_reference=factory.Sequence(
                        lambda n: f"wfl_fake_dummy_id_{n!s}"
                    ),
                    submitted_for_signature_on=None,
                    student_signed_on=now,
                    organization_signed_on=now,
                )
            )

        contracts_to_sign = contracts_to_sign[:2]
        contracts_to_sign_ids = [contract.id for contract in contracts_to_sign]
        contracts_to_sign_ids.append(uuid.uuid4())

        with self.assertRaises(NoContractToSignError) as context:
            organization.signature_backend_references_to_sign(
                contracts_ids=contracts_to_sign_ids
            )

        self.assertEqual(
            str(context.exception),
            "Some contracts are not available for this organization.",
        )

    def test_models_organization_signature_backend_references_to_sign_empty(self):
        """Should return an empty list if no references to sign exists."""
        organization = factories.OrganizationFactory()
        self.assertEqual(organization.signature_backend_references_to_sign(), [])

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_models_organization_contracts_signature_link(self):
        """Should return a signature link."""
        now = timezone.now()
        organization = factories.OrganizationFactory()
        relations = factories.CourseProductRelationFactory.create_batch(
            3,
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        for relation in relations:
            factories.ContractFactory(
                order__state=enums.ORDER_STATE_VALIDATED,
                order__product=relation.product,
                order__course=relation.course,
                order__organization=organization,
                signature_backend_reference=factory.Sequence(
                    lambda n: f"wfl_fake_dummy_id_{n!s}"
                ),
                submitted_for_signature_on=now,
                student_signed_on=now,
            )
        user = factories.UserFactory()

        invitation_url = organization.contracts_signature_link(user=user)
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_models_organization_contracts_signature_link_specified_ids(self):
        """Should return a signature link for specified contract ids."""
        now = timezone.now()
        organization = factories.OrganizationFactory()
        relations = factories.CourseProductRelationFactory.create_batch(
            3,
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contracts = []
        for relation in relations:
            contract = factories.ContractFactory(
                order__state=enums.ORDER_STATE_VALIDATED,
                order__product=relation.product,
                order__course=relation.course,
                order__organization=organization,
                signature_backend_reference=factory.Sequence(
                    lambda n: f"wfl_fake_dummy_id_{n!s}"
                ),
                submitted_for_signature_on=now,
                student_signed_on=now,
            )
            contracts.append(contract)
        user = factories.UserFactory()

        contracts_to_sign = contracts[:2]
        contracts_to_sign_ids = [contract.id for contract in contracts_to_sign]

        invitation_url = organization.contracts_signature_link(
            user=user, contracts_ids=contracts_to_sign_ids
        )
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_models_organization_contracts_signature_link_empty(self):
        """Should fail if no references to sign exists.""" ""
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()

        with self.assertRaises(NoContractToSignError) as context:
            organization.contracts_signature_link(user=user)

        self.assertEqual(
            str(context.exception),
            "No contract to sign for this organization.",
        )
