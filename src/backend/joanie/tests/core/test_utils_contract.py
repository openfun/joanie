"""Test suite to generate a ZIP archive of signed contract PDF files in bytes utility"""
import random
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.core.utils import contract as contract_utility
from joanie.core.utils import contract_definition as contract_definition_utility
from joanie.core.utils import issuers
from joanie.payment.factories import InvoiceFactory


class UtilsContractTestCase(TestCase):
    """Test suite to generate a ZIP archive of signed contract PDF files in bytes utility"""

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
        relation = factories.CourseProductRelationFactory()
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
                        enums.ORDER_STATE_SUBMITTED,
                        enums.ORDER_STATE_VALIDATED,
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
        From a Course Product Relation product object, we should be able to find the contract's
        signature backend references that are attached to the validated orders only for a specific
        course and product. It should return an iterator with signature backend references.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory()
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
                order__state=enums.ORDER_STATE_VALIDATED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
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
        From an Organization object, if there are no signed contracts attached to the organization,
        it should return an empty iterator.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory()
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
                        enums.ORDER_STATE_SUBMITTED,
                        enums.ORDER_STATE_VALIDATED,
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
        From an Organization object, we should be able to find the contract's signature backend
        references from signed contracts. It should return an iterator with signature backend
        references.
        """
        users = factories.UserFactory.create_batch(3)
        relation = factories.CourseProductRelationFactory()
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
                order__state=enums.ORDER_STATE_VALIDATED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
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
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CERTIFICATE)
        relation = factories.CourseProductRelationFactory(
            product=product,
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
                        enums.ORDER_STATE_SUBMITTED,
                        enums.ORDER_STATE_VALIDATED,
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
        From a Course Product Relation product object, we should be able to find the signed
        contract signature backend references that are attached to the 'validated' Orders of a
        specific Enrollment.
        """
        users = factories.UserFactory.create_batch(3)
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CERTIFICATE)
        relation = factories.CourseProductRelationFactory(
            product=product,
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
                order__state=enums.ORDER_STATE_VALIDATED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
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
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CERTIFICATE)
        relation = factories.CourseProductRelationFactory(
            product=product, organizations=[organization]
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
                order__state=enums.ORDER_STATE_VALIDATED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
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
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CERTIFICATE)
        relation = factories.CourseProductRelationFactory(
            product=product, organizations=[organization_course_supplier]
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
                order__state=enums.ORDER_STATE_VALIDATED,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
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

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_utils_contract_get_pdf_bytes_of_contracts(self):
        """
        When we call this method with 2 existing signature backend references at the signature
        provider, it should return a list with 2 PDF bytes.
        """
        contract1 = factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_4",
            definition_checksum="1234",
            submitted_for_signature_on=timezone.now(),
            context="a small context content 1",
        )
        InvoiceFactory(order=contract1.order)
        contract2 = factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_5",
            definition_checksum="5678",
            submitted_for_signature_on=timezone.now(),
            context="a small context content 2",
        )
        InvoiceFactory(order=contract2.order)
        backend_signature_references = [
            "wfl_fake_dummy_4",
            "wfl_fake_dummy_5",
        ]

        pdf_bytes_list = contract_utility.get_pdf_bytes_of_contracts(
            backend_signature_references
        )

        self.assertEqual(len(pdf_bytes_list), 2)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_utils_contract_get_pdf_bytes_of_contracts_with_one_wrong_reference(self):
        """
        When we call this method with 1 non-existent signature backend reference at the signature
        provider, it should raise an error with the reference that has failed.
        """
        contract = factories.ContractFactory(
            signature_backend_reference="wfl_fake_dummy_4",
            definition_checksum="1234",
            submitted_for_signature_on=timezone.now(),
            context="a small context content 1",
        )
        InvoiceFactory(order=contract.order)
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
        relation = factories.CourseProductRelationFactory()
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
                state=enums.ORDER_STATE_VALIDATED,
            )
            InvoiceFactory(
                order=order,
                recipient_address__address="1 Rue de L'Exemple",
                recipient_address__postcode=75000,
                recipient_address__city="Paris",
            )
            context = contract_definition_utility.generate_document_context(
                order.product.contract_definition, users[index], order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=signature_reference,
                definition_checksum="1234",
                context=context,
                signed_on=timezone.now(),
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

                        self.assertRegex(document_text, r"CONTRACT")
                        self.assertRegex(document_text, r"DEFINITION")
                        self.assertRegex(
                            document_text, r"1 Rue de L'Exemple 75000, Paris."
                        )
        # Clear file zip archive in storages
        storage.delete(generated_zip_archive_name)
