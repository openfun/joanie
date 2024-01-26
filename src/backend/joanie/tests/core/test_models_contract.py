"""Tests for the Contract Model"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories, models

# pylint: disable=too-many-public-methods


class ContractModelTestCase(TestCase):
    """
    Test case for the Contract Model
    """

    def _check_signature_dates_constraint(
        self,
        submitted_for_signature_on: bool = False,
        student_signed_on: bool = False,
        organization_signed_on: bool = False,
        should_raise: bool = False,
    ):
        """
        Check the signature dates constraints.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        data = {
            "order": order,
            "context": {"foo": "bar"},
            "definition_checksum": "1234",
        }
        signature_date = datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC"))
        submitted_for_signature_on = (
            signature_date if submitted_for_signature_on else None
        )
        student_signed_on = signature_date if student_signed_on else None
        organization_signed_on = signature_date if organization_signed_on else None

        if not should_raise:
            factories.ContractFactory(
                **data,
                submitted_for_signature_on=submitted_for_signature_on,
                student_signed_on=student_signed_on,
                organization_signed_on=organization_signed_on,
            )
            return

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                **data,
                submitted_for_signature_on=submitted_for_signature_on,
                student_signed_on=student_signed_on,
                organization_signed_on=organization_signed_on,
            )
        self.assertEqual(
            str(context.exception), "{'__all__': ['Signature dates are incoherent.']}"
        )

    def _check_signature_dates_constraint_raises(
        self,
        submitted_for_signature_on: bool = False,
        student_signed_on: bool = False,
        organization_signed_on: bool = False,
    ):
        self._check_signature_dates_constraint(
            submitted_for_signature_on,
            student_signed_on,
            organization_signed_on,
            should_raise=True,
        )

    def _check_signature_dates_constraint_passes(
        self,
        submitted_for_signature_on: bool = False,
        student_signed_on: bool = False,
        organization_signed_on: bool = False,
    ):
        self._check_signature_dates_constraint(
            submitted_for_signature_on,
            student_signed_on,
            organization_signed_on,
            should_raise=False,
        )

    def test_models_contract_incoherent_signature_dates_constraint_fails(
        self,
    ):
        """
        Constraint fails if:

        | submitted_for_signature_on | student_signed_on | organization_signed_on |
        |----------------------------|-------------------|------------------------|
        | None                       | Defined           | None                   |
        | None                       | None              | Defined                |
        | Defined                    | None              | Defined                |
        | Defined                    | Defined           | Defined                |
        """
        expected_fails = [
            (False, True, False),
            (False, False, True),
            (True, False, True),
            (True, True, True),
        ]

        for expected_fail in expected_fails:
            self._check_signature_dates_constraint_raises(*expected_fail)

    def test_models_contract_incoherent_signature_dates_constraint_passes(
        self,
    ):
        """
        Constraint pass if:

        | submitted_for_signature_on | student_signed_on | organization_signed_on |
        |----------------------------|-------------------|------------------------|
        | None                       | None              | None                   |
        | Defined                    | None              | None                   |
        | Defined                    | Defined           | None                   |
        | None                       | Defined           | Defined                |
        """
        expected_passes = [
            (False, False, False),
            (True, False, False),
            (True, True, False),
            (False, True, True),
        ]
        for expected_pass in expected_passes:
            self._check_signature_dates_constraint_passes(*expected_pass)

    def test_models_contract_incoherent_signature_dates_none(
        self,
    ):
        """
        'student_signed_on' and 'submitted_for_signature_on' can both be None.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order, student_signed_on=None, submitted_for_signature_on=None
        )
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.student_signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    def test_models_contract_incoherent_signature_dates_student_signed_on(
        self,
    ):
        """
        'student_signed_on' can be None and 'submitted_for_signature_on' can be set
        with a datetime value.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            student_signed_on=None,
            submitted_for_signature_on=datetime(
                2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
            ),
        )
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.student_signed_on)
        self.assertIsNotNone(contract.submitted_for_signature_on)

    def test_models_contract_incoherent_signature_dates_submitted_for_signature_on(
        self,
    ):
        """
        'submitted_for_signature_on' can be None and 'student_signed_on' can be set
        with a datetime value.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            organization_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            submitted_for_signature_on=None,
        )
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNotNone(contract.student_signed_on)

    def test_models_contract_signature_backend_reference_constraint(
        self,
    ):
        """
        If 'signature_backend_reference' is set, either 'student_signed_on'
        or 'submitted_for_signature_on' must also be set.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(
                contract_definition=factories.ContractDefinitionFactory()
            ),
        )

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context={"foo": "bar"},
                definition_checksum="1234",
                signature_backend_reference="wfl_dummy",
                student_signed_on=None,
                submitted_for_signature_on=None,
            )

        message = (
            "{'__all__': "
            "['Make sure to have a date attached to the signature backend reference.']}"
        )
        self.assertEqual(str(context.exception), message)

    def test_models_contract_signature_backend_reference_student_signed_on(
        self,
    ):
        """
        If 'signature_backend_reference' is set, the 'student_signed_on' datetime
        can be set as long as the 'submitted_for_signature' datetime is not set.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            signature_backend_reference="wfl_dummy",
            submitted_for_signature_on=None,
            student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
            organization_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        contract = models.Contract.objects.get()
        self.assertIsNotNone(contract.signature_backend_reference)
        self.assertIsNotNone(contract.student_signed_on)
        self.assertIsNone(contract.submitted_for_signature_on)

    def test_models_contract_signature_backend_reference_submitted_for_signature_on(
        self,
    ):
        """
        If 'signature_backend_reference' is set, the 'submitted_for_signature_on' datetime can
        be set as long as the 'student_signed_on' datetime is not set.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory(
            order=order,
            context={"foo": "bar"},
            definition_checksum="1234",
            signature_backend_reference="wfl_dummy",
            student_signed_on=None,
            submitted_for_signature_on=datetime(
                2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
            ),
        )
        contract = models.Contract.objects.get()
        self.assertIsNotNone(contract.signature_backend_reference)
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.student_signed_on)

    def test_models_contract_generate_complete_constraints(
        self,
    ):
        """
        If the 'definition_checksum' field is set, the 'context' field should also be set, and
        reciprocally.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )
        message = "{'__all__': ['Make sure to complete all fields when generating a contract.']}"

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context={"foo": "bar"}, definition_checksum=None
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context={"foo": "bar"}, definition_checksum=""
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context={}, definition_checksum="1234"
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(order=order, context={}, definition_checksum=None)
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order, context=None, definition_checksum="1234"
            )
        self.assertEqual(str(context.exception), message)

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(order=order, context=None, definition_checksum="")
        self.assertEqual(str(context.exception), message)

    def test_models_contract_generate_complete_success_both_are_none(
        self,
    ):
        """
        'context' and 'definition_checksum' can both be None when the contract is not signed and
        not submitted for signature.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory(order=order, context=None, definition_checksum=None)
        contract = models.Contract.objects.get()
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.definition_checksum)

    def test_models_contract_student_signed_on_when_context_and_definition_checksum_both_none(
        self,
    ):
        """
        'context' and 'definition_checksum' can not be left empty when the contract is signed.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        message = (
            "{'__all__': ['Make sure to complete all fields before signing contract.']}"
        )
        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context=None,
                definition_checksum=None,
                student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
                organization_signed_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
            )

        self.assertEqual(str(context.exception), message)

    def test_models_contract_student_signed_on_when_context_is_none_only(self):
        """
        'student_signed_on' and 'definition_checksum' have values and
        'context' is set to None.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context=None,
                definition_checksum="1234",
                student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
                organization_signed_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ["
                "'Make sure to complete all fields when generating a contract.', "
                "'Make sure to complete all fields before signing contract.']}"
            ),
        )

    def test_models_contract_student_signed_on_when_context_and_student_signed_on_are_both_none(
        self,
    ):
        """
        A signed document should have a context and a definition checksum set.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        message_student_signed_on = (
            "{'__all__': ['Make sure to complete all fields before signing contract.']}"
        )
        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context=None,
                definition_checksum=None,
                student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
                organization_signed_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
            )

        self.assertEqual(str(context.exception), message_student_signed_on)

    def test_models_contract_student_signed_on_context_empty_dict_or_none_and_checksum_is_none(
        self,
    ):
        """
        'context' is an empty dictionary or 'None', and 'definition_checksum' is 'None'
        when 'student_signed_on' has a value.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory.create(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(),
        )

        with self.assertRaises(ValidationError) as context:
            factories.ContractFactory(
                order=order,
                context={},
                definition_checksum=None,
                student_signed_on=datetime(2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")),
                organization_signed_on=datetime(
                    2023, 9, 20, 8, 0, tzinfo=ZoneInfo("UTC")
                ),
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ["
                "'Make sure to complete all fields when generating a contract.',"
                " 'Make sure to complete all fields before signing contract.']}"
            ),
        )

    def test_models_contract_tag_submission_for_signature(self):
        """
        After submitting a file to get sign, tag submission updates the Contract with the data
        provided from the signature provider. It should give new values to the following fields :
        'signature_backend_reference', 'context', 'definition_checksum' and
        'submitted_for_signature_on'.
        """
        order = factories.OrderFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        contract = factories.ContractFactory(order=order)

        contract.tag_submission_for_signature(
            reference="wlf_id_fake",
            checksum="fake_file_hash",
            context="small context content",
        )

        contract.refresh_from_db()
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertEqual(contract.signature_backend_reference, "wlf_id_fake")
        self.assertEqual(contract.definition_checksum, "fake_file_hash")
        self.assertEqual(contract.context, "small context content")

    def test_models_contract_reset_submission_for_signature(self):
        """
        After submitting a file to get sign at the signature provider and the signer refuses to
        sign the file, the contract should be resetted with None values for the fields :
        'signature_backend_reference', 'context', 'definition_checksum'
        and 'submitted_for_signature_on'.
        """
        order = factories.OrderFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )

        contract.reset_submission_for_signature()

        contract.refresh_from_db()
        self.assertIsNone(contract.context)
        self.assertIsNone(contract.submitted_for_signature_on)
        self.assertIsNone(contract.signature_backend_reference)
        self.assertIsNone(contract.definition_checksum)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    )
    def test_model_contract_is_eligible_for_signature_must_be_true(self):
        """
        When the contract field 'submitted_for_signature_on' date is still within
        the validity period to be signed, it should return True to get signed.
        """
        order = factories.OrderFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )

        response = contract.is_eligible_for_signing()

        self.assertEqual(response, True)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    )
    def test_model_contract_is_eligible_for_signature_must_be_false(self):
        """
        When the contract field 'submitted_for_signature_on' is not within the validity
        period to be signed, it should return False to get signed.
        """
        order = factories.OrderFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_id_fake",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )

        response = contract.is_eligible_for_signing()

        self.assertEqual(response, False)

    def test_model_contract_is_eligible_for_signature_must_be_false_because_its_not_submitted(
        self,
    ):
        """
        If the contract does not have a value for 'submitted_for_signature_on', it should
        return False to get signed.
        """
        order = factories.OrderFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        contract = factories.ContractFactory(
            order=order,
            submitted_for_signature_on=None,
        )

        response = contract.is_eligible_for_signing()

        self.assertEqual(response, False)

    def test_models_contract_get_abilities_anonymous(self):
        """Check abilities returned for an anonymous user."""
        contract = factories.ContractFactory()
        user = AnonymousUser()

        assert contract.get_abilities(user) == {"sign": False}

    def test_models_contract_get_abilities_authenticated(self):
        """Check abilities returned for an authenticated user."""
        contract = factories.ContractFactory()
        user = factories.UserFactory()

        assert contract.get_abilities(user) == {"sign": False}

    def test_models_contract_get_abilities_owner(self):
        """Check abilities returned for the owner of an organization."""
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=enums.OWNER,
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        assert contract.get_abilities(user) == {"sign": True}

    def test_models_contract_get_abilities_administrator(self):
        """Check abilities returned for the administrator of a organization."""
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=enums.ADMIN,
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        assert contract.get_abilities(user) == {"sign": False}

    def test_models_contract_get_abilities_member_user(self):
        """Check abilities returned for the member of a organization."""
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=enums.MEMBER,
        )
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        assert contract.get_abilities(user) == {"sign": False}

    def test_models_contract_get_abilities_preset_role(self):
        """No query is done if the role is preset e.g. with query annotation."""
        user = factories.UserFactory()
        contract = factories.ContractFactory()
        contract.order.organization.user_role = "owner"

        with self.assertNumQueries(0):
            assert contract.get_abilities(user) == {"sign": True}

    def test_models_contract_avoid_to_create_an_order_with_an_ended_course_run(self):
        """
        An order cannot be generated if the course run is archived. It should raise a
        ValidationError.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        course = factories.CourseFactory(
            organizations=[organization], users=[[user, enums.OWNER]]
        )
        course_run = factories.CourseRunFactory(
            is_listed=True,
            course=course,
            state=models.CourseState.ONGOING_OPEN,
            languages="fr",
            resource_link="http://openedx.test/courses/course-v1:edx+00000+0/course/",
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        closing_date = django_timezone.now() - timedelta(days=1)
        # closing enrollments and the course run
        course_run.enrollment_end = closing_date
        course_run.end = closing_date
        course_run.save()

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                owner=enrollment.user,
                enrollment=enrollment,
                course=None,
                product__type=enums.PRODUCT_TYPE_CERTIFICATE,
                product__courses=[enrollment.course_run.course],
                state=enums.ORDER_STATE_VALIDATED,
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'course': ['The order cannot be generated on "
                "course run that is in archived state.']}"
            ),
        )
