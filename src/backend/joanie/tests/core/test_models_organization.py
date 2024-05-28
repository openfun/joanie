"""
Test suite for organization models
"""

import uuid

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.utils import timezone

import factory

from joanie.core import enums, factories, models
from joanie.core.exceptions import NoContractToSignError
from joanie.tests.base import BaseAPITestCase


# pylint: disable=too-many-public-methods
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
                "sign_contracts": False,
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
                "sign_contracts": False,
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
                "sign_contracts": True,
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
                "sign_contracts": False,
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
                "sign_contracts": False,
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
                "sign_contracts": False,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
            (
                tuple(contract.id for contract in reversed(contracts_to_sign)),
                tuple(
                    contract.signature_backend_reference
                    for contract in reversed(contracts_to_sign)
                ),
            ),
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                contract_ids=contracts_to_sign_ids
            ),
            (
                tuple(contract.id for contract in reversed(contracts_to_sign)),
                tuple(
                    contract.signature_backend_reference
                    for contract in reversed(contracts_to_sign)
                ),
            ),
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                    order__state=enums.ORDER_STATE_COMPLETED,
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
                contract_ids=contracts_to_sign_ids
            )

        self.assertEqual(
            str(context.exception),
            "Some contracts are not available for this organization.",
        )

    def test_models_organization_signature_backend_references_to_sign_empty(self):
        """Should return an empty list if no references to sign exists."""
        organization = factories.OrganizationFactory()
        self.assertEqual(organization.signature_backend_references_to_sign(), ((), ()))

    def test_models_organization_contracts_signature_link(self):
        """Should return a signature link."""
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
                order__state=enums.ORDER_STATE_COMPLETED,
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

        (invitation_url, contract_ids) = organization.contracts_signature_link(
            user=user
        )
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)
        contracts_to_sign_ids = [contract.id for contract in contracts]
        self.assertCountEqual(contracts_to_sign_ids, contract_ids)

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
                order__state=enums.ORDER_STATE_COMPLETED,
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

        (invitation_url, contract_ids) = organization.contracts_signature_link(
            user=user, contract_ids=contracts_to_sign_ids
        )
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)
        self.assertCountEqual(contract_ids, contracts_to_sign_ids)

    def test_models_organization_contracts_signature_link_empty(self):
        """Should fail if no references to sign exists."""
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()

        with self.assertRaises(NoContractToSignError) as context:
            organization.contracts_signature_link(user=user)

        self.assertEqual(
            str(context.exception),
            "No contract to sign for this organization.",
        )

    def test_models_organization_fields_contact_phone_number_only_formatted(self):
        """The `contact_phone` field should be formatted without spaces on save."""
        organization1 = factories.OrganizationFactory(
            contact_phone="00 11 1 23 45 67 89"
        )
        organization1.save()

        self.assertEqual(organization1.contact_phone, "0011123456789")

        organization2 = factories.OrganizationFactory(contact_phone="01 23 45 67 89")
        organization2.save()

        self.assertEqual(organization2.contact_phone, "0123456789")

    def test_models_organization_fields_contact_phone_number_special_characters_normalized(
        self,
    ):
        """
        The `contact_phone` field should be normalized without non-digits and spaces on save.
        The field should only include digits and '+' characters.
        """
        organization = factories.OrganizationFactory(contact_phone="+1 (123) 123-4567")
        organization.save()

        self.assertEqual(organization.contact_phone, "+11231234567")

        organization2 = factories.OrganizationFactory(
            contact_phone="+(33) 1 23 45 67 89"
        )
        organization2.save()

        self.assertEqual(organization2.contact_phone, "+33123456789")

    def test_models_organization_fields_contact_phone_number_empty(self):
        """The `contact_phone` field should remain empty if initially empty."""
        organization = factories.OrganizationFactory(contact_phone="")
        organization.save()

        self.assertEqual(organization.contact_phone, "")

    def test_models_organization_fields_contact_phone_number_no_digits(self):
        """The `contact_phone` field should be empty if no digits are provided."""
        organization = factories.OrganizationFactory(contact_phone="abc wrong number")
        organization.save()

        self.assertEqual(organization.contact_phone, "")

    def test_models_organization_signatory_representative_fields_must_be_set_no_profession(
        self,
    ):
        """
        If the field `signatory_representative` is set and `signatory_representative_profession`
        is missing, it should raise an error. Both fields must be set if one is set.
        """

        with self.assertRaises(ValidationError) as context:
            factories.OrganizationFactory(
                signatory_representative="John Doe",
                signatory_representative_profession=None,
            )

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Both signatory representative fields must be set.']}",
        )

    def test_models_organization_signatory_representative_fields_must_be_set_no_representative(
        self,
    ):
        """
        If the field `signatory_representative_profession` is set and `signatory_representative`
        is missing, it should raise an error. Both fields must be set if one is set.
        """

        with self.assertRaises(ValidationError) as context:
            factories.OrganizationFactory(
                signatory_representative=None,
                signatory_representative_profession="Board of Directors",
            )

        self.assertEqual(
            str(context.exception),
            "{'__all__': ['Both signatory representative fields must be set.']}",
        )

    def test_models_organization_signatory_representative_fields_are_both_set(self):
        """
        We should be able to create an Organization when both fields
        `signatory_representative_profession` and `signatory_representative` are set.
        """
        organization = factories.OrganizationFactory(
            signatory_representative="John Doe",
            signatory_representative_profession="Board of Directors",
        )
        self.assertEqual(organization.signatory_representative, "John Doe")
        self.assertEqual(
            organization.signatory_representative_profession, "Board of Directors"
        )
