"""
Test suite for order models
"""

# pylint: disable=too-many-lines,too-many-public-methods
import json
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import mock

from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone as django_timezone

from joanie.core import enums, factories
from joanie.core.models import Contract, CourseState
from joanie.core.utils import contract_definition
from joanie.payment.factories import BillingAddressDictFactory, InvoiceFactory
from joanie.tests.base import BaseLogMixinTestCase


class OrderModelsTestCase(TestCase, BaseLogMixinTestCase):
    """Test suite for the Order model."""

    maxDiff = None

    def test_models_order_enrollment_was_created_by_order(self):
        """
        The enrollment linked to an order, must not orginate from an order.
        This is because, being flagged with "was_created_by_order" as True, this enrollment will
        not be listed directly on the student dashboard. It will be visible only behind one of
        the orders listed on the dashboard.
        """
        course_run = factories.CourseRunFactory(
            state=CourseState.FUTURE_OPEN,
            is_listed=True,
        )
        factories.ProductFactory(target_courses=[course_run.course], type="enrollment")
        enrollment = factories.EnrollmentFactory(
            course_run=course_run, was_created_by_order=True
        )

        certificate_product = factories.ProductFactory(
            courses=[course_run.course], type="certificate"
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                product=certificate_product, course=None, enrollment=enrollment
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': [\"Orders can't be placed on enrollments originating "
                'from an order."]}'
            ),
        )

    def test_models_order_state_property_validated_when_free(self):
        """
        When an order relies on a free product, its state should be automatically
        validated without any invoice and without calling the validate()
        method.
        """
        courses = factories.CourseFactory.create_batch(2)
        # Create a free product
        product = factories.ProductFactory(courses=courses, price=0)
        order = factories.OrderFactory(product=product, total=0.00)
        order.submit()

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_models_order_enrollment_owned_by_enrollment_user(self):
        """The enrollment linked to an order, must belong to the order owner."""
        course_run = factories.CourseRunFactory(
            state=CourseState.FUTURE_OPEN,
            is_listed=True,
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run)

        certificate_product = factories.ProductFactory(
            courses=[course_run.course], type="certificate"
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                # Forcing the user to something else than the enrollment user
                owner=factories.UserFactory(),
                product=certificate_product,
                course=None,
                enrollment=enrollment,
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': ['The enrollment should belong to the owner of this order.']}"
            ),
        )

    def test_models_order_course_enrollment_constraint_product_certificate(self):
        """
        Orders for "certificate" type products can only be linked to an enrollment.
        The course field must remain null.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type="certificate")
        organization = product.course_relations.get().organizations.first()
        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
            course_run__course=course,
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                product=product, course=course, enrollment=enrollment
            )
        self.assertEqual(
            str(context.exception),
            "{'course': ['course field should be left empty for certificate products.']}",
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                organization=organization, product=product, course=None, enrollment=None
            )
        self.assertEqual(
            str(context.exception),
            "{'enrollment': ['enrollment field should be set for certificate products.']}",
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(product=product, course=course, enrollment=None)
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': ['enrollment field should be set for certificate products.'], "
                "'course': ['course field should be left empty for certificate products.']}"
            ),
        )

        factories.OrderFactory(
            organization=organization,
            product=product,
            course=None,
            enrollment=enrollment,
        )

    def _enrollment_constraint_product_on_courses(self, product_type):
        """
        Factorized test code to test "course" and "enrollment" fields for
        products that are sold on the syllabus.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], type=product_type)
        organization = product.course_relations.get().organizations.first()
        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
            course_run__course=course,
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                product=product, course=course, enrollment=enrollment
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'enrollment': ['enrollment field should be left empty "
                f"for {product_type} products.']}}"
            ),
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                organization=organization, product=product, course=None, enrollment=None
            )
        self.assertEqual(
            str(context.exception),
            (
                "{'course': ['course field should be set "
                f"for {product_type} products.']}}"
            ),
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                organization=organization,
                product=product,
                course=None,
                enrollment=enrollment,
            )
        self.assertEqual(
            str(context.exception),
            (
                f"{{'course': ['course field should be set for {product_type} products.'], "
                "'enrollment': ['enrollment field should be left empty "
                f"for {product_type} products.']}}"
            ),
        )

        factories.OrderFactory(
            product=product,
            course=course,
            enrollment=None,
        )

    def test_models_order_course_enrollment_constraint_product_credential(self):
        """
        Orders for "credential" type products can only be linked to a course.
        The enrollment field must remain null.
        """
        self._enrollment_constraint_product_on_courses("credential")

    def test_models_order_course_enrollment_constraint_product_enrollment(self):
        """
        Orders for "enrollment" type products can only be linked to a course.
        The enrollment field must remain null.
        """
        self._enrollment_constraint_product_on_courses("enrollment")

    def test_models_order_course_owner_product_unique_not_canceled(self):
        """
        There should be a db constraint forcing uniqueness of orders with the same course,
        product and owner fields that are not canceled.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product)

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                owner=order.owner,
                product=product,
                course=course,
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['"
                "An order for this product and course already exists."
                "']}"
            ),
        )

    def test_models_order_enrollment_owner_product_unique_not_canceled(self):
        """
        There should be a db constraint forcing uniqueness of orders with the same enrollment,
        product and owner fields that are not canceled.
        """
        enrollment = factories.EnrollmentFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE, courses=[enrollment.course_run.course]
        )
        order = factories.OrderFactory(
            product=product,
            enrollment=enrollment,
            course=None,
        )

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                owner=order.owner,
                product=product,
                enrollment=enrollment,
                course=None,
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['"
                "An order for this product and enrollment already exists."
                "']}"
            ),
        )

    @staticmethod
    def test_models_order_course_owner_product_unique_canceled():
        """
        Canceled orders are not taken into account for uniqueness on the course, product and
        owner triplet.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(
            product=product, state=enums.ORDER_STATE_CANCELED
        )

        factories.OrderFactory(owner=order.owner, product=product, course=order.course)

    def test_models_order_course_runs_relation_sorted_by_position(self):
        """The product/course relation should be sorted by position."""
        courses = factories.CourseFactory.create_batch(5)
        product = factories.ProductFactory(target_courses=courses)

        # Create an order link to the product
        order = factories.OrderFactory(product=product)
        order.submit(billing_address=BillingAddressDictFactory())

        target_courses = order.target_courses.order_by("product_target_relations")
        self.assertCountEqual(target_courses, courses)

        position = 0
        for target_course in target_courses:
            course_position = target_course.product_target_relations.get().position
            self.assertGreaterEqual(course_position, position)
            position = course_position

    def test_models_order_course_in_product_new(self):
        """
        An order's course should be included in the target courses of its related product at
        the moment the order is created.
        """
        course = factories.CourseFactory()
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(title="Traçabilité")
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )
        self.assertTrue(product.courses.filter(id=course.id).exists())

        other_course = factories.CourseFactory(title="Mathématiques")

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(
                course=other_course, product=product, organization=organization
            )

        self.assertEqual(
            context.exception.messages,
            [
                'This order cannot be linked to the product "Traçabilité", '
                'the course "Mathématiques" and the organization "fun".'
            ],
        )

    @staticmethod
    def test_models_order_course_in_product_existing():
        """
        An order's course can be absent from the related product target courses when updating an
        existing order.
        """
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=courses)
        order = factories.OrderFactory(product=product)
        order.course = factories.CourseFactory()
        order.save()

    def test_models_order_state_property(self):
        """
        Order state property is set and related with invoice.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(title="Traçabilité", courses=[course])
        order = factories.OrderFactory(
            product=product, state=enums.ORDER_STATE_SUBMITTED
        )

        # 2 - When an invoice is linked to the order, and the method validate() is
        # called its state is `validated`
        InvoiceFactory(order=order, total=order.total)
        order.flow.validate()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        # 3 - When order is canceled, its state is `canceled`
        order.flow.cancel()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_models_order_get_target_enrollments(self):
        """
        Order model implements a `get_target_enrollments` method to retrieve enrollments
        related to the order instance.
        """
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            state=CourseState.ONGOING_OPEN,
            is_listed=False,
        )
        product = factories.ProductFactory(
            price="0.00", target_courses=[cr1.course, cr2.course]
        )
        order = factories.OrderFactory(product=product)
        order.submit()

        # - As the two product's target courses have only one course run, order owner
        #   should have been automatically enrolled to those course runs.
        with self.assertNumQueries(1):
            self.assertEqual(len(order.get_target_enrollments()), 2)
        self.assertEqual(len(order.get_target_enrollments(is_active=True)), 2)
        self.assertEqual(len(order.get_target_enrollments(is_active=False)), 0)

        # - Then order is canceled so user should be unenrolled to course runs.
        order.flow.cancel()
        self.assertEqual(len(order.get_target_enrollments()), 2)
        self.assertEqual(len(order.get_target_enrollments(is_active=True)), 0)
        self.assertEqual(len(order.get_target_enrollments(is_active=False)), 2)

    def test_models_order_target_course_runs_property(self):
        """
        Order model has a target course runs property to retrieve all course runs
        related to the order instance.
        """
        [course1, course2] = factories.CourseFactory.create_batch(2)
        [cr1, cr2] = factories.CourseRunFactory.create_batch(2, course=course1)
        [cr3, cr4] = factories.CourseRunFactory.create_batch(2, course=course2)
        product = factories.ProductFactory(target_courses=[course1, course2])

        # - Link cr3 to the product course relations
        relation = product.target_course_relations.get(course=course2)
        relation.course_runs.add(cr3)

        # - Create an order link to the product
        order = factories.OrderFactory(product=product)
        order.submit(billing_address=BillingAddressDictFactory())

        # - Update product course relation, order course relation should not be impacted
        relation.course_runs.set([])

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            # - product.target_course_runs should return all course runs
            course_runs = product.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 4)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3, cr4])

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            # - order.target_course_runs should only return cr1, cr2, cr3
            course_runs = order.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 3)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3])

    def test_models_order_create_target_course_relations_on_submit(self):
        """
        When an order is submitted, product target courses should be copied to the order
        """
        product = factories.ProductFactory(
            target_courses=factories.CourseFactory.create_batch(2)
        )
        order = factories.OrderFactory(product=product)

        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)
        self.assertEqual(order.target_courses.count(), 0)

        # Then we submit the order
        order.submit(billing_address=BillingAddressDictFactory())

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(order.target_courses.count(), 2)

    def test_models_order_dont_create_target_course_relations_on_resubmit(self):
        """
        When an order is submitted again, product target courses should not be copied
        again to the order
        """
        product = factories.ProductFactory(
            target_courses=factories.CourseFactory.create_batch(2)
        )
        order = factories.OrderFactory(product=product)

        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)
        self.assertEqual(order.target_courses.count(), 0)

        # Then we submit the order
        order.submit(billing_address=BillingAddressDictFactory())

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(order.target_courses.count(), 2)

        # Unfortunately, order transitions to pending state
        order.flow.pending()

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # So we need to submit it again
        order.submit(billing_address=BillingAddressDictFactory())

        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)
        self.assertEqual(order.target_courses.count(), product.target_courses.count())

    @mock.patch(
        "joanie.signature.backends.dummy.DummySignatureBackend.submit_for_signature",
        return_value=("mocked", "mocked"),
    )
    def test_models_order_submit_for_signature_document_title(
        self, _mock_submit_for_signature
    ):
        """
        Order submit_for_signature should set the document title uploaded
        to the signature backend according to the current date, the related
        course and the order pk.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        order.submit_for_signature(user=user)
        now = django_timezone.now()

        _mock_submit_for_signature.assert_called_once()
        # Check that the title is correctly formatted
        self.assertEqual(
            _mock_submit_for_signature.call_args[1]["title"],
            f"{now.strftime('%Y-%m-%d')}_{order.course.code}_{order.pk}",
        )
        self.assertEqual(_mock_submit_for_signature.call_args[1]["order"], order)
        self.assertIsInstance(
            _mock_submit_for_signature.call_args[1]["file_bytes"], bytes
        )

    def test_models_order_submit_for_signature_fails_when_the_product_has_no_contract_definition(
        self,
    ):
        """
        When a product does not have a contract definition attached to it, it should raise an
        error when trying to submit the order's contract for a signature.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            product=factories.ProductFactory(contract_definition=None),
        )

        with (
            self.assertRaises(ValidationError) as context,
            self.assertLogs("joanie") as logger,
        ):
            order.submit_for_signature(user=user)

        self.assertEqual(
            str(context.exception),
            '["No contract definition attached to the contract\'s product."]',
        )

        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "No contract definition attached to the contract's product.",
                    {"order": dict, "product": dict},
                ),
            ],
        )

    def test_models_order_submit_for_signature_fails_because_order_is_not_state_validate(
        self,
    ):
        """
        When the order is not in state 'validated', it should not be possible to submit for
        signature.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=random.choice(
                [
                    enums.ORDER_STATE_CANCELED,
                    enums.ORDER_STATE_SUBMITTED,
                    enums.ORDER_STATE_DRAFT,
                    enums.ORDER_STATE_PENDING,
                ]
            ),
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        with (
            self.assertRaises(ValidationError) as context,
            self.assertLogs("joanie") as logger,
        ):
            order.submit_for_signature(user=user)

        self.assertEqual(
            str(context.exception),
            "['Cannot submit an order that is not yet validated.']",
        )

        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Cannot submit an order that is not yet validated.",
                    {"order": dict},
                ),
            ],
        )

    def test_models_order_submit_for_signature_with_a_brand_new_contract(
        self,
    ):
        """
        When the order's product has a contract definition, and the order doesn't have yet
        a contract generated, it will generate one and it should return an invitation link to go
        sign the contract. While it is generated, it should update contract's fields values :
        'submitted_for_signature_on', 'context', 'definition_checksum',
        'signature_backend_reference'.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        raw_invitation_link = order.submit_for_signature(user=user)

        order.contract.refresh_from_db()
        self.assertIsNotNone(order.contract)
        self.assertIsNotNone(order.contract.student_signed_on)
        self.assertIsNotNone(order.contract.submitted_for_signature_on)
        self.assertIsNotNone(order.contract.context)
        self.assertIsNotNone(order.contract.definition)
        self.assertIsNotNone(order.contract.signature_backend_reference)
        self.assertIsNotNone(order.contract.definition_checksum)
        self.assertIn(
            "https://dummysignaturebackend.fr/?requestToken=", raw_invitation_link
        )

    def test_models_order_submit_for_signature_existing_contract_with_same_context_and_still_valid(
        self,
    ):
        """
        When an order is resubmitting his contract for a signature procedure that is still
        within the validity period and the context has not changed since last submission, it should
        return an invitation link and not change the fields values :
        'submitted_for_signature_on', 'context', 'definition_checksum',
        'signature_backend_reference' of the contract.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        context = contract_definition.generate_document_context(
            contract_definition=order.product.contract_definition,
            user=user,
            order=order,
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id_1",
            definition_checksum="fake_dummy_file_hash_1",
            context=context,
            submitted_for_signature_on=django_timezone.now(),
        )

        invitation_url = order.submit_for_signature(user=user)

        contract.refresh_from_db()
        self.assertEqual(
            contract.context, json.loads(DjangoJSONEncoder().encode(context))
        )
        self.assertEqual(contract.definition_checksum, "fake_dummy_file_hash_1")
        self.assertEqual(
            contract.signature_backend_reference,
            "wfl_fake_dummy_id_1",
        )
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)

    def test_models_order_submit_for_signature_with_contract_context_has_changed_and_still_valid(
        self,
    ):
        """
        When an order is resubmitting his contract for a signature that is still within the
        validity period and the context has changed since last submission, it should return
        an invitation link in return and update the fields values of the contract :
        'submitted_for_signature_on', 'context', 'definition_checksum',
        'signature_backend_reference'
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id_123",
            definition_checksum="fake_test_file_hash_1",
            context="content",
            submitted_for_signature_on=django_timezone.now(),
        )

        invitation_url = order.submit_for_signature(user=user)

        contract.refresh_from_db()
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)
        self.assertIn("wfl_fake_dummy_", contract.signature_backend_reference)
        self.assertIn("fake_dummy_file_hash", contract.definition_checksum)
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNotNone(contract.student_signed_on)

    @override_settings(
        JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS=60 * 60 * 24 * 15,
    )
    def test_models_order_submit_for_signature_contract_same_context_but_passed_validity_period(
        self,
    ):
        """
        When an order is resubmitting his contract for a signature procedure and the context has
        not changed since last submission, but validity period is passed. It should return an
        invitation link and update the contract's fields with new values for :
        'submitted_for_signature_on', 'context', 'definition_checksum',
        and 'signature_backend_reference'.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__target_courses=[
                factories.CourseFactory.create(
                    course_runs=[
                        factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
                    ]
                )
            ],
        )
        context = contract_definition.generate_document_context(
            contract_definition=order.product.contract_definition,
            user=user,
            order=order,
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id_1",
            definition_checksum="fake_test_file_hash_1",
            context=context,
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )

        with self.assertLogs("joanie") as logger:
            invitation_url = order.submit_for_signature(user=user)

        enrollment = user.enrollments.first()

        contract.refresh_from_db()
        self.assertEqual(
            contract.context, json.loads(DjangoJSONEncoder().encode(context))
        )
        self.assertIn("https://dummysignaturebackend.fr/?requestToken=", invitation_url)
        self.assertIn("fake_dummy_file_hash", contract.definition_checksum)
        self.assertNotEqual("wfl_fake_dummy_id_1", contract.signature_backend_reference)
        self.assertIsNotNone(contract.submitted_for_signature_on)
        self.assertIsNotNone(contract.student_signed_on)
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "WARNING",
                    "contract is not eligible for signing: signature validity period has passed",
                    {
                        "contract": dict,
                        "submitted_for_signature_on": datetime,
                        "signature_validity_period": int,
                        "valid_until": datetime,
                    },
                ),
                (
                    "INFO",
                    f"Document signature refused for the contract '{contract.id}'",
                ),
                (
                    "INFO",
                    f"Active Enrollment {enrollment.pk} has been created",
                ),
                ("INFO", f"Student signed the contract '{contract.id}'"),
                (
                    "INFO",
                    f"Mail for '{contract.signature_backend_reference}' "
                    f"is sent from Dummy Signature Backend",
                ),
            ],
        )

    def test_models_order_submit_for_signature_but_contract_is_already_signed_should_fail(
        self,
    ):
        """
        When an order already have his contract signed, it should raise an error because
        we cannot submit it again.
        """
        user = factories.UserFactory()
        factories.UserAddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        now = django_timezone.now()
        factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id_1",
            definition_checksum="fake_test_file_hash_1",
            context="context",
            submitted_for_signature_on=None,
            student_signed_on=now,
            organization_signed_on=now,
        )

        with (
            self.assertRaises(PermissionDenied) as context,
            self.assertLogs("joanie") as logger,
        ):
            order.submit_for_signature(user=user)

        self.assertEqual(
            str(context.exception),
            "Contract is already signed by the student, cannot resubmit.",
        )
        self.assertLogsEquals(
            logger.records,
            [
                (
                    "ERROR",
                    "Contract is already signed by the student, cannot resubmit.",
                    {"contract": dict},
                ),
            ],
        )

    def test_models_order_organization_required_if_not_draft_constraint(self):
        """
        Check the db constraint forbidding a non draft order to not have a linked
        organization
        """
        for order_state in enums.ORDER_STATE_CHOICES:
            if order_state[0] not in enums.ORDER_STATE_DRAFT:
                order = factories.OrderFactory()
                order.organization = None
                order.state = order_state[0]
                with self.assertRaises(ValidationError) as context:
                    order.save()
                self.assertEqual(
                    str(context.exception),
                    (
                        "{'__all__': ['Order should have an organization if not in draft state']}"
                    ),
                )

    def test_models_order_get_equivalent_course_run_dates(self):
        """
        Check that order's product dates are processed
        by aggregating target course runs dates as expected.
        """
        earliest_start_date = django_timezone.now() - timedelta(days=1)
        latest_end_date = django_timezone.now() + timedelta(days=2)
        latest_enrollment_start_date = django_timezone.now() - timedelta(days=2)
        earliest_enrollment_end_date = django_timezone.now() + timedelta(days=1)
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            is_listed=True,
            course=course,
            start=earliest_start_date,
            end=latest_end_date,
            enrollment_start=latest_enrollment_start_date,
            enrollment_end=earliest_enrollment_end_date,
            languages="fr",
        )
        product = factories.ProductFactory(target_courses=[course])
        order = factories.OrderFactory(product=product)
        factories.OrderTargetCourseRelationFactory(
            course=course, order=order, position=1
        )
        expected_result = {
            "start": earliest_start_date,
            "end": latest_end_date,
            "enrollment_start": latest_enrollment_start_date,
            "enrollment_end": earliest_enrollment_end_date,
        }

        self.assertEqual(order.get_equivalent_course_run_dates(), expected_result)

    def test_models_order_target_course_runs_property_distinct(self):
        """
        In any case, target course runs should be distinct.
        """
        # - Create two products with one target course and three course runs
        target_course = factories.CourseFactory()
        course_runs = factories.CourseRunFactory.create_batch(
            3, course=target_course, state=CourseState.ONGOING_OPEN
        )
        [p0, p1] = factories.ProductFactory.create_batch(
            2, target_courses=[target_course]
        )
        # The first product only use a course run subset
        p0.target_course_relations.first().course_runs.add(course_runs[0])

        # - Create orders on each products
        [o0, *_] = factories.OrderFactory.create_batch(
            5,
            product=p0,
            state=enums.ORDER_STATE_VALIDATED,
        )
        [o1, *_] = factories.OrderFactory.create_batch(
            5,
            product=p1,
            state=enums.ORDER_STATE_VALIDATED,
        )

        self.assertEqual(o0.target_course_runs.count(), 1)
        self.assertEqual(o1.target_course_runs.count(), 3)

    def test_models_order_submit_for_signature_check_contract_context_course_section_after_create(
        self,
    ):
        """
        When we call `submit_for_signature` with a validated order, it will generate the context
        to add to the contract. In the contract context, we should find the values in the course
        section where the `course_start`, `course_end`, `course_price` and
        `course_effort` are string type.
        """
        user = factories.UserFactory()
        factories.SiteConfigFactory(
            site=Site.objects.get_current(),
            terms_and_conditions="## Terms ",
        )
        user_address = factories.UserAddressFactory(owner=user)
        organization = factories.OrganizationFactory()
        factories.OrganizationAddressFactory(organization=organization)
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product=factories.ProductFactory(
                contract_definition=factories.ContractDefinitionFactory(),
                title="You will know that you know you don't know",
                price="1202.99",
                target_courses=[
                    factories.CourseFactory(
                        course_runs=[
                            factories.CourseRunFactory(
                                start="2024-02-01T10:00:00+00:00",
                                end="2024-05-31T20:00:00+00:00",
                                enrollment_start="2024-02-01T12:00:00+00:00",
                                enrollment_end="2024-02-01T12:00:00+00:00",
                            )
                        ]
                    )
                ],
            ),
            course=factories.CourseFactory(
                organizations=[organization],
                effort=timedelta(hours=13, minutes=30, seconds=12),
            ),
        )
        order = factories.OrderFactory(
            owner=user,
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_VALIDATED,
            main_invoice=InvoiceFactory(recipient_address=user_address),
        )
        factories.OrderTargetCourseRelationFactory(
            course=relation.course, order=order, position=1
        )

        order.submit_for_signature(user=user)

        contract = Contract.objects.get(order=order)
        course_dates = order.get_equivalent_course_run_dates()

        # Course effort check
        self.assertIsInstance(order.course.effort, timedelta)
        self.assertIsInstance(contract.context["course"]["effort"], str)
        self.assertEqual(
            order.course.effort, timedelta(hours=13, minutes=30, seconds=12)
        )
        self.assertEqual(contract.context["course"]["effort"], "P0DT13H30M12S")

        # Course start check
        self.assertIsInstance(course_dates["start"], datetime)
        self.assertIsInstance(contract.context["course"]["start"], str)
        self.assertEqual(
            course_dates["start"], datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            contract.context["course"]["start"], "2024-02-01T10:00:00+00:00"
        )

        # Course end check
        self.assertIsInstance(course_dates["end"], datetime)
        self.assertIsInstance(contract.context["course"]["end"], str)
        self.assertEqual(
            course_dates["end"], datetime(2024, 5, 31, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(contract.context["course"]["end"], "2024-05-31T20:00:00+00:00")

        # Pricing check
        self.assertIsInstance(order.total, Decimal)
        self.assertIsInstance(contract.context["course"]["price"], str)
        self.assertEqual(order.total, Decimal("1202.99"))
        self.assertEqual(contract.context["course"]["price"], "1202.99")

    def test_models_order_avoid_to_create_with_an_archived_course_run(self):
        """
        An order cannot be generated if the course run is archived. It should raise a
        ValidationError.
        """
        course_run = factories.CourseRunFactory(
            is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)

        # Update the course run to archived it
        closing_date = django_timezone.now() - timedelta(days=1)
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
                "{'course': ['The order cannot be created on "
                "course run that is in archived state.']}"
            ),
        )

    def test_api_order_allow_to_cancel_with_archived_course_run(self):
        """
        An order should be cancelable even if the related course run is archived.
        """
        course_run = factories.CourseRunFactory(
            is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            owner=enrollment.user,
            enrollment=enrollment,
            course=None,
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__courses=[enrollment.course_run.course],
            state=enums.ORDER_STATE_VALIDATED,
        )

        # Update the course run to archived it
        closing_date = django_timezone.now() - timedelta(days=1)
        course_run.enrollment_end = closing_date
        course_run.end = closing_date
        course_run.save()

        order.flow.cancel()

        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
