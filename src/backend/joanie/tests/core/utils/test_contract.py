"""Test suite to generate a ZIP archive of signed contract PDF files in bytes utility"""

import random
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.test import TestCase
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.core.utils import contract as contract_utility
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers
from joanie.payment.factories import InvoiceFactory


# pylint:disable=too-many-public-methods
class UtilsContractTestCase(TestCase):
    """Test suite to generate a ZIP archive of signed contract PDF files in bytes utility"""

    def test_utils_contract_get_signature_backend_references_states(
        self,
    ):
        """
        From a Course Product Relation product object, we should be able to find the
        contract's signature backend references that are attached to the validated
        orders only for a specific course and product. It should return an iterator with
        signature backend references.
        All orders but the canceled ones should be returned.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                relation = factories.CourseProductRelationFactory(
                    product__contract_definition=factories.ContractDefinitionFactory()
                )
                contract = factories.ContractFactory(
                    # order__owner=users[index],
                    order__product=relation.product,
                    order__course=relation.course,
                    order__state=state,
                    definition_checksum="1234",
                    context={"foo": "bar"},
                    student_signed_on=timezone.now(),
                    organization_signed_on=timezone.now(),
                )

                signature_backend_references_generator = (
                    contract_utility.get_signature_backend_references(
                        course_product_relation=relation, organization=None
                    )
                )
                signature_backend_references_list = list(
                    signature_backend_references_generator
                )

                if state == enums.ORDER_STATE_CANCELED:
                    self.assertEqual(len(signature_backend_references_list), 0)
                    self.assertEqual(signature_backend_references_list, [])
                else:
                    self.assertEqual(len(signature_backend_references_list), 1)
                    self.assertEqual(
                        signature_backend_references_list,
                        [contract.signature_backend_reference],
                    )

    def test_utils_contract_get_signature_backend_references_with_no_signed_contracts_yet(
        self,
    ):
        """
        From a Course Product Relation product object, we should be able to find the contract's
        signature backend references that are attached to the 'validated' orders only for a
        specific course and product. If all orders found do not have the state validated, it should
        return an empty generator.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=relation.course,
                order__state=random.choice(
                    [
                        enums.ORDER_STATE_CANCELED,
                        enums.ORDER_STATE_DRAFT,
                        enums.ORDER_STATE_PENDING,
                        enums.ORDER_STATE_COMPLETED,
                    ]
                ),
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                submitted_for_signature_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation, organization=None
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 0)
        self.assertEqual(signature_backend_references_list, [])

    def test_utils_contract_get_signature_backend_references_with_many_signed_contracts_with_cpr(
        self,
    ):
        """
        From a Course Product Relation product object, we should be able to find the
        contract's signature backend references that are attached to the validated
        orders only for a specific course and product. It should return an iterator with
        signature backend references.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=relation.course,
                order__state=enums.ORDER_STATE_COMPLETED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation, organization=None
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 3)
        self.assertEqual(
            signature_backend_references_list,
            ["wfl_fake_dummy_1", "wfl_fake_dummy_2", "wfl_fake_dummy_3"],
        )

    def test_utils_contract_get_signature_backend_references_no_signed_contracts_from_organization(
        self,
    ):
        """
        From an Organization object, if there are no signed contracts attached to the
        organization, it should return an empty iterator.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        organization = relation.organizations.first()
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=relation.course,
                order__state=random.choice(
                    [
                        enums.ORDER_STATE_CANCELED,
                        enums.ORDER_STATE_DRAFT,
                        enums.ORDER_STATE_PENDING,
                        enums.ORDER_STATE_COMPLETED,
                    ]
                ),
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                submitted_for_signature_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=None, organization=organization
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 0)
        self.assertEqual(signature_backend_references_list, [])

    def test_utils_contract_get_signature_backend_references_signed_contracts_from_organization(
        self,
    ):
        """
        From an Organization object, we should be able to find the contract's signature
        backend references from signed contracts. It should return an iterator with
        signature backend references.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory()
        )
        organization = relation.organizations.first()
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=relation.course,
                order__state=enums.ORDER_STATE_COMPLETED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=None, organization=organization
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 3)
        self.assertEqual(
            signature_backend_references_list,
            ["wfl_fake_dummy_1", "wfl_fake_dummy_2", "wfl_fake_dummy_3"],
        )

    def test_utils_contract_get_signature_backend_references_no_signed_contracts_from_enrollment(
        self,
    ):
        """
        From a Course Product Relation product object where it has an Enrollment but there are no
        signed contracts yet, we should be not able to find the contract's signature backend
        reference and get an empty iterator in return.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            enrollment = factories.EnrollmentFactory(
                user=users[index],
                course_run__course=relation.course,
                course_run__state=models.CourseState.ONGOING_OPEN,
                course_run__is_listed=True,
            )
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=None,
                order__enrollment=enrollment,
                order__state=random.choice(
                    [
                        enums.ORDER_STATE_CANCELED,
                        enums.ORDER_STATE_DRAFT,
                        enums.ORDER_STATE_PENDING,
                        enums.ORDER_STATE_COMPLETED,
                    ]
                ),
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                submitted_for_signature_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation, organization=None
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 0)
        self.assertEqual(signature_backend_references_list, [])

    def test_utils_contract_get_signature_backend_references_signed_contracts_from_enrollment(
        self,
    ):
        """
        From a Course Product Relation product object, we should be able to find the
        signed contract signature backend references that are attached to the
        'validated' Orders of a specific Enrollment.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            enrollment = factories.EnrollmentFactory(
                user=users[index],
                course_run__course=relation.course,
                course_run__state=models.CourseState.ONGOING_OPEN,
                course_run__is_listed=True,
            )
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=None,
                order__enrollment=enrollment,
                order__state=enums.ORDER_STATE_COMPLETED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation, organization=None
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 3)
        self.assertEqual(
            signature_backend_references_list,
            ["wfl_fake_dummy_1", "wfl_fake_dummy_2", "wfl_fake_dummy_3"],
        )

    def test_utils_contract_get_signature_backend_reference_extra_filters_org_access_of_user(
        self,
    ):
        """
        When we add the extra filters parameter where we want to filter if the requesting user has
        the rights on the Organization that is attached to an existing Course Product Relation
        object in the get signature backend reference method, we should be able to find the signed
        contract signature backend references.
        """
        organization = factories.OrganizationFactory()
        requesting_user = factories.UserFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=requesting_user
        )
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=[organization],
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        users = factories.UserFactory.create_batch(3)
        for index, signature_reference in enumerate(signature_reference_choices):
            enrollment = factories.EnrollmentFactory(
                user=users[index],
                course_run__course=relation.course,
                course_run__state=models.CourseState.ONGOING_OPEN,
                course_run__is_listed=True,
            )
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=None,
                order__enrollment=enrollment,
                order__state=enums.ORDER_STATE_COMPLETED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )
        extra_filters = {"order__organization__accesses__user_id": requesting_user.id}

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation,
                organization=None,
                extra_filters=extra_filters,
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 3)
        self.assertEqual(
            signature_backend_references_list,
            ["wfl_fake_dummy_1", "wfl_fake_dummy_2", "wfl_fake_dummy_3"],
        )

    def test_utils_contract_get_signature_backend_reference_extra_filters_without_user_org_access(
        self,
    ):
        """
        From a Course Product Relation product object, we should not be able to find signature
        backend references if the user has no access to the organization when we add an extra
        filter in the queryset. It should return an empty iterator.
        """
        requesting_user = factories.UserFactory()
        factories.UserOrganizationAccessFactory(
            organization=factories.OrganizationFactory(), user=requesting_user
        )
        organization_course_supplier = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            product__type=enums.PRODUCT_TYPE_CERTIFICATE,
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=[organization_course_supplier],
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        users = factories.UserFactory.create_batch(3)
        for index, signature_reference in enumerate(signature_reference_choices):
            enrollment = factories.EnrollmentFactory(
                user=users[index],
                course_run__course=relation.course,
                course_run__state=models.CourseState.ONGOING_OPEN,
                course_run__is_listed=True,
            )
            factories.ContractFactory(
                order__owner=users[index],
                order__product=relation.product,
                order__course=None,
                order__enrollment=enrollment,
                order__state=enums.ORDER_STATE_COMPLETED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )
        extra_filters = {"order__organization__accesses__user_id": requesting_user.id}

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation,
                organization=None,
                extra_filters=extra_filters,
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 0)
        self.assertEqual(
            signature_backend_references_list,
            [],
        )

    def test_utils_contract_get_pdf_bytes_of_contracts_with_empty_list_as_input_parameter(
        self,
    ):
        """
        When parsing an empty list as input parameter to fetch PDF bytes of contracts method, it
        should return an empty list.
        """
        output = contract_utility.get_pdf_bytes_of_contracts(
            signature_backend_references=[]
        )

        self.assertEqual(output, [])

    def test_utils_contract_get_pdf_bytes_of_contracts(self):
        """
        When we call this method with 2 existing signature backend references at the signature
        provider, it should return a list with 2 PDF bytes.
        """
        factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_4",
            definition_checksum="1234",
            submitted_for_signature_on=timezone.now(),
            context="a small context content 1",
        )
        factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_5",
            definition_checksum="5678",
            submitted_for_signature_on=timezone.now(),
            context="a small context content 2",
        )
        backend_signature_references = [
            "wfl_fake_dummy_4",
            "wfl_fake_dummy_5",
        ]

        pdf_bytes_list = contract_utility.get_pdf_bytes_of_contracts(
            backend_signature_references
        )

        self.assertEqual(len(pdf_bytes_list), 2)

    def test_utils_contract_get_pdf_bytes_of_contracts_with_one_wrong_reference(self):
        """
        When we call this method with 1 non-existent signature backend reference at the signature
        provider, it should raise an error with the reference that has failed.
        """
        factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_4",
            definition_checksum="1234",
            submitted_for_signature_on=timezone.now(),
            context="a small context content 1",
        )
        backend_signature_references = [
            "wfl_fake_dummy_4",
            "wfl_wrong_dummy_5",
        ]

        with self.assertRaises(ValidationError) as context:
            contract_utility.get_pdf_bytes_of_contracts(backend_signature_references)

        self.assertEqual(
            str(context.exception),
            "['Cannot download contract with reference id : wfl_wrong_dummy_5.']",
        )

    def test_utils_contract_generate_zip_archive_fails_because_input_list_is_empty(
        self,
    ):
        """
        When we give an empty list to generate ZIP archive method, it should raise an
        error because it requires a non-empty list.
        """
        with self.assertRaises(ValueError) as context:
            contract_utility.generate_zip_archive(
                pdf_bytes_list=[], user_uuid=uuid4(), zip_uuid=uuid4()
            )

        self.assertEqual(
            str(context.exception),
            "You should provide a non-empty list of PDF bytes to generate ZIP archive.",
        )

    # pylint: disable=too-many-locals
    def test_utils_contract_generate_zip_archive_success(self):
        """
        When we give a list of PDF files in bytes to generate ZIP archive method, it should return
        the filename of the ZIP archive and save the ZIP archive into storages. There should be 3
        contracts in the ZIP archive.
        """
        storage = storages["contracts"]
        users = factories.UserFactory.create_batch(3)
        requesting_user = factories.UserFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(
                title="Contract definition title"
            )
        )
        signature_reference_choices = [
            "wfl_fake_dummy_4",
            "wfl_fake_dummy_5",
            "wfl_fake_dummy_6",
        ]
        files_in_bytes = []
        for index, signature_reference in enumerate(signature_reference_choices):
            order = factories.OrderFactory(
                owner=users[index],
                product=relation.product,
                course=relation.course,
                state=enums.ORDER_STATE_COMPLETED,
                main_invoice=InvoiceFactory(
                    recipient_address__address="1 Rue de L'Exemple",
                    recipient_address__postcode=75000,
                    recipient_address__city="Paris",
                    recipient_address__country="FR",
                ),
            )
            context = contract_definition_utility.generate_document_context(
                order.product.contract_definition, users[index], order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context=context,
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )
            pdf_bytes_file = issuers.generate_document(
                order.product.contract_definition.name, context=context
            )
            files_in_bytes.append(pdf_bytes_file)

        expected_zip_uuid = uuid4()
        generated_zip_archive_name = contract_utility.generate_zip_archive(
            pdf_bytes_list=files_in_bytes,
            user_uuid=requesting_user.pk,
            zip_uuid=expected_zip_uuid,
        )

        self.assertEqual(
            generated_zip_archive_name, f"{requesting_user.pk}_{expected_zip_uuid}.zip"
        )

        # Retrieve the ZIP archive from storages
        with storage.open(generated_zip_archive_name) as storage_zip_archive:
            with ZipFile(storage_zip_archive, "r") as zip_archive_elements:
                file_names = zip_archive_elements.namelist()
                # Check the amount of files inside the ZIP archive
                self.assertEqual(len(file_names), 3)
                # Check the file name of each pdf in bytes
                for index, pdf_filename in enumerate(file_names):
                    self.assertEqual(pdf_filename, f"contract_{index}.pdf")
                    # Check the content of the PDF inside the ZIP archive
                    with zip_archive_elements.open(pdf_filename) as pdf_file:
                        document_text = pdf_extract_text(
                            BytesIO(pdf_file.read())
                        ).replace("\n", "")

                        self.assertIn("Contract definition title", document_text)
                        self.assertIn(
                            "1 Rue de L'Exemple, 75000 Paris (FR)",
                            document_text,
                        )
        # Clear file zip archive in storages
        storage.delete(generated_zip_archive_name)

    def test_utils_contract_get_signature_backend_references_with_course_product_relation_and_org(
        self,
    ):
        """
        If the course product relation is shared accross 2 organizations, when passing the course
        product relation UUID and the organization UUID, we should be able to retrieve only the
        contract that is attached to the organization parsed in parameters.
        """
        learners = factories.UserFactory.create_batch(2)
        organizations = factories.OrganizationFactory.create_batch(2)
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=organizations,
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
        ]
        for index, signature_reference in enumerate(signature_reference_choices):
            factories.ContractFactory(
                order__organization=organizations[index],
                order__owner=learners[index],
                order__product=relation.product,
                order__course=relation.course,
                order__state=enums.ORDER_STATE_COMPLETED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )

        signature_backend_references_generator = (
            contract_utility.get_signature_backend_references(
                course_product_relation=relation, organization=organizations[0]
            )
        )
        signature_backend_references_list = list(signature_backend_references_generator)

        self.assertEqual(len(signature_backend_references_list), 1)
        self.assertEqual(
            signature_backend_references_list,
            ["wfl_fake_dummy_1"],
        )

    def test_utils_contract_organization_has_owner_without_owners_returns_false(
        self,
    ):
        """
        When calling the method `order_has_organization_owner` with a order uuid but
        the organization has not set any owner members yet with organization access,
        it should return False.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
            state=enums.ORDER_STATE_COMPLETED,
        )
        factories.ContractFactory(
            order=order, definition=order.product.contract_definition
        )

        self.assertFalse(contract_utility.order_has_organization_owner(order))

    def test_utils_contract_organization_has_owner_returns_true(
        self,
    ):
        """
        When calling the method `order_has_organization_owner` with a order uuid and
        the organization has set owner members with organizationa access, it should return True.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
            state=enums.ORDER_STATE_COMPLETED,
        )
        factories.ContractFactory(
            order=order, definition=order.product.contract_definition
        )

        # When the organization has set some owners with access rights of "owner"
        factories.UserOrganizationAccessFactory.create_batch(
            3, organization=order.organization, role="owner"
        )

        self.assertTrue(contract_utility.order_has_organization_owner(order))

    def test_utils_contract_get_signature_references_student_has_signed(self):
        """
        Should return the signature backend references of orders that are owned
        by an organization and where it still awaits the organization's signature.
        Contracts with a cancelled order should not be returned.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                user = factories.UserFactory()
                order = factories.OrderFactory(
                    owner=user,
                    product__contract_definition=factories.ContractDefinitionFactory(),
                    state=state,
                )
                factories.ContractFactory(
                    order=order,
                    definition=order.product.contract_definition,
                    signature_backend_reference="wfl_fake_dummy_id",
                    definition_checksum="1234",
                    context="context",
                    submitted_for_signature_on=timezone.now(),
                    student_signed_on=timezone.now(),
                    organization_signed_on=None,
                )
                order_found = contract_utility.get_signature_references(
                    organization_id=order.organization.id, student_has_not_signed=False
                )

                if state == enums.ORDER_STATE_CANCELED:
                    self.assertEqual(list(order_found), [])
                else:
                    self.assertEqual(list(order_found), ["wfl_fake_dummy_id"])

    def test_utils_contract_get_signature_references_student_has_not_signed(self):
        """
        Should return the signature backend references that are owned by an organization
        and where there is no signature yet but has been submitted for signature.
        Contracts with a cancelled order should not be returned.
        """
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                user = factories.UserFactory()
                order = factories.OrderFactory(
                    owner=user,
                    product__contract_definition=factories.ContractDefinitionFactory(),
                    state=state,
                )
                factories.ContractFactory(
                    order=order,
                    definition=order.product.contract_definition,
                    signature_backend_reference="wfl_fake_dummy_id",
                    definition_checksum="1234",
                    context="context",
                    submitted_for_signature_on=timezone.now(),
                    student_signed_on=None,
                    organization_signed_on=None,
                )
                order_found = contract_utility.get_signature_references(
                    organization_id=order.organization.id, student_has_not_signed=True
                )

                if state == enums.ORDER_STATE_CANCELED:
                    self.assertEqual(list(order_found), [])
                else:
                    self.assertEqual(list(order_found), ["wfl_fake_dummy_id"])

    def test_utils_contract_get_signature_references_should_not_find_order(self):
        """
        Should return an empty queryset because the only order of the organization was
        fully signed already.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory(
            owner=user,
            product__contract_definition=factories.ContractDefinitionFactory(),
            state=enums.ORDER_STATE_COMPLETED,
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
        )

        order_found = contract_utility.get_signature_references(
            organization_id=order.organization.id, student_has_not_signed=False
        )

        self.assertEqual(list(order_found), [])
        self.assertTrue(contract.is_fully_signed)

    def test_utils_contract_get_signature_references_returns_generator_empty(self):
        """
        Should return the generator object with no result because there is no order
        for the given organization.
        """
        organization = factories.OrganizationFactory()

        order_found = contract_utility.get_signature_references(
            organization_id=organization.id, student_has_not_signed=True
        )
        order_found_list = list(order_found)

        self.assertEqual(order_found_list, [])

    def test_utils_contract_update_signatories_for_contracts_but_no_awaiting_contract_to_sign(
        self,
    ):
        """
        Should return an empty list because there is no contract to sign for the organization.
        """
        organization = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=[organization],
        )
        order = factories.OrderFactory(
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_COMPLETED,
            organization=organization,
        )
        factories.ContractFactory(
            order=order,
            signature_backend_reference="wfl_fake_dummy_0",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
        )

        contract_updated = contract_utility.update_signatories_for_contracts(
            organization_id=order.organization.id
        )

        self.assertEqual(contract_updated["organization_signatories_updated"], [])
        self.assertEqual(
            models.Contract.objects.filter(
                submitted_for_signature_on__isnull=False,
                order__state=enums.ORDER_STATE_COMPLETED,
                order__organization_id=organization.id,
                organization_signed_on__isnull=False,
                student_signed_on__isnull=False,
            ).count(),
            0,
        )

    def test_utils_contract_update_signatories_for_contracts(self):
        """
        Should return a list of all signature backend references that are attached to the
        organization only and got updated successfully.
        """
        organization = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=[organization],
        )
        learners = factories.UserFactory.create_batch(3)
        signature_reference_choices = ["wfl_fake_dummy_0", "wfl_fake_dummy_1"]
        for index, reference in enumerate(signature_reference_choices):
            order = factories.OrderFactory(
                owner=learners[index],
                product=relation.product,
                course=relation.course,
                state=enums.ORDER_STATE_COMPLETED,
                organization=organization,
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context="context",
                submitted_for_signature_on=timezone.now(),
                student_signed_on=timezone.now(),
                organization_signed_on=None,
            )
        order = factories.OrderFactory(
            owner=learners[2],
            product=relation.product,
            course=relation.course,
            state=enums.ORDER_STATE_COMPLETED,
            organization=organization,
        )
        # This contract will need a full update for student and organization
        factories.ContractFactory(
            order=order,
            signature_backend_reference="wfl_fake_dummy_2",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=None,
            organization_signed_on=None,
        )
        # Contract for another organization that should not be returned in updated results
        factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_3",
            definition_checksum="5678",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=timezone.now(),
            organization_signed_on=None,
            context="a small context content 2",
        )

        contracts_updated = contract_utility.update_signatories_for_contracts(
            organization_id=order.organization.id
        )

        self.assertEqual(
            contracts_updated,
            {
                "organization_signatories_updated": [
                    "wfl_fake_dummy_1",
                    "wfl_fake_dummy_0",
                ],
                "all_signatories_updated": ["wfl_fake_dummy_2"],
            },
        )
        self.assertEqual(
            models.Contract.objects.filter(
                submitted_for_signature_on__isnull=False,
                order__state=enums.ORDER_STATE_COMPLETED,
                order__organization_id=organization.id,
                organization_signed_on__isnull=True,
                student_signed_on__isnull=True,
            ).count(),
            1,
        )
        self.assertEqual(
            models.Contract.objects.filter(
                submitted_for_signature_on__isnull=False,
                order__state=enums.ORDER_STATE_COMPLETED,
                order__organization_id=organization.id,
                organization_signed_on__isnull=True,
                student_signed_on__isnull=False,
            ).count(),
            2,
        )
