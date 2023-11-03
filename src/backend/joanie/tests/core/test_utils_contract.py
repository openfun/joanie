"""Test suite to generate a zipfile for signed contract PDF files in bytes utility"""
import random
from io import BytesIO
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.utils import contract, contract_definition, issuers


class UtilsContractTestCase(TestCase):
    """Test suite to generate a zipfile of signed contract PDF files in bytes utility"""

    def setUp(self):
        default_storage.delete("signed_contracts.zip")

    def test_utils_contract_get_signature_backend_references_with_no_signed_contracts_yet(
        self,
    ):
        """
        From a course product relation product object, we should be able to find the contract's
        signature backend references that are attached to the 'validated' orders only for a
        specific course and product. If all orders found do not have the state validated, it should
        return an empty list.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
                state=random.choice(
                    [
                        enums.ORDER_STATE_CANCELED,
                        enums.ORDER_STATE_DRAFT,
                        enums.ORDER_STATE_PENDING,
                        enums.ORDER_STATE_SUBMITTED,
                        enums.ORDER_STATE_VALIDATED,
                    ]
                ),
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                submitted_for_signature_on=timezone.now(),
            )

        references_found = contract.get_signature_backend_references(
            course_product_relation=relation, organization=None
        )

        self.assertEqual(references_found, [])

    def test_utils_contract_get_signature_backend_references_with_many_signed_contracts_with_cpr(
        self,
    ):
        """
        From a course product relation product object, we should be able to find the contract's
        signature backend references that are attached to the validated orders only for a specific
        course and product. It should return a list with signature backend references.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
                state=enums.ORDER_STATE_VALIDATED,
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
            )

        references_found = contract.get_signature_backend_references(
            course_product_relation=relation, organization=None
        )

        self.assertEqual(
            references_found,
            ["wfl_fake_dummy_1", "wfl_fake_dummy_2", "wfl_fake_dummy_3"],
        )

    def test_utils_contract_get_signature_backend_references_no_signed_contracts_from_organization(
        self,
    ):
        """
        From an organization object, if there are no signed contracts attached to the organization,
        it should return an empty list.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        organization = relation.organizations.all().first()
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
                state=random.choice(
                    [
                        enums.ORDER_STATE_CANCELED,
                        enums.ORDER_STATE_DRAFT,
                        enums.ORDER_STATE_PENDING,
                        enums.ORDER_STATE_SUBMITTED,
                        enums.ORDER_STATE_VALIDATED,
                    ]
                ),
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                submitted_for_signature_on=timezone.now(),
            )

        references_found = contract.get_signature_backend_references(
            course_product_relation=None, organization=organization
        )

        self.assertEqual(
            references_found,
            [],
        )

    def test_utils_contract_get_signature_backend_references_signed_contracts_from_organization(
        self,
    ):
        """
        From an organization object, we should be able to find the contract's signature
        backend references from signed contracts. It should return a list with signature backend
        references.
        """
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        organization = relation.organizations.all().first()
        signature_reference_choices = [
            "wfl_fake_dummy_1",
            "wfl_fake_dummy_2",
            "wfl_fake_dummy_3",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
                state=enums.ORDER_STATE_VALIDATED,
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context={"foo": "bar"},
                signed_on=timezone.now(),
            )

        references_found = contract.get_signature_backend_references(
            course_product_relation=None, organization=organization
        )

        self.assertEqual(
            references_found,
            ["wfl_fake_dummy_1", "wfl_fake_dummy_2", "wfl_fake_dummy_3"],
        )

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_utils_contract_fetch_pdf_bytes_of_contracts(self):
        """
        When we call this method with 2 existing signature backend references at the signature
        provider, it should return the a list with 2 PDF bytes.
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

        pdf_bytes_list = contract.fetch_pdf_bytes_of_contracts(
            backend_signature_references
        )

        self.assertEqual(len(pdf_bytes_list), 2)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_utils_contract_fetch_pdf_bytes_of_contracts_with_one_wrong_reference(self):
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
            contract.fetch_pdf_bytes_of_contracts(backend_signature_references)

        self.assertEqual(
            str(context.exception),
            "['Cannot download contract with reference id : wfl_wrong_dummy_5.']",
        )

    def test_utils_contract_generate_zipfile_fails_because_input_list_is_empty(self):
        """
        When we give an empty list to generate zipfile archive method, it should raise an
        error because it requires a non-empty list.
        """
        empty_list = []

        with self.assertRaises(ValueError) as context:
            contract.generate_zipfile(pdf_bytes_list=empty_list)

        self.assertEqual(
            str(context.exception),
            "You should provide a non-empty list of PDF bytes to generate ZIP archive.",
        )

    # pylint: disable=too-many-locals
    def test_utils_contract_generate_zipfile_success(self):
        """
        When we give a list of PDF files in bytes to generate zipfile method, it should return
        the filename and save the ZIP archive into default storage.
        We will verify what was added into the zipfile, we should find 3 files within.
        """
        expected_filename_archive = "signed_contracts_extract.zip"
        users = factories.UserFactory.create_batch(3)
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        signature_reference_choices = [
            "wfl_fake_dummy_4",
            "wfl_fake_dummy_5",
            "wfl_fake_dummy_6",
        ]
        files_in_bytes = []
        for index, reference in enumerate(signature_reference_choices):
            user = users[index]
            order = factories.OrderFactory(
                owner=user,
                product=relation.product,
                course=relation.course,
                state=enums.ORDER_STATE_VALIDATED,
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                signed_on=timezone.now(),
            )
            pdf_bytes_file = issuers.generate_document(
                order.product.contract_definition.name, context=context
            )
            files_in_bytes.append(pdf_bytes_file)

        generated_zipfile_filename = contract.generate_zipfile(files_in_bytes)

        self.assertEqual(generated_zipfile_filename, expected_filename_archive)

        # Check the content of the ZIP archive and retrieve from default storage
        with default_storage.open(expected_filename_archive) as storage_zip_archive:
            with ZipFile(storage_zip_archive, "r") as zip_archive:
                file_names = zip_archive.namelist()
                # Check the amount of files inside the ZIP archive
                self.assertEqual(len(file_names), 3)
                # Check the file name of each pdf in bytes
                for index, pdf_filename in enumerate(file_names):
                    self.assertEqual(pdf_filename, f"contract_{index}.pdf")
                    # Check the content of the PDF inside the ZIP archive
                    with zip_archive.open(pdf_filename) as pdf_file:
                        document_text = pdf_extract_text(
                            BytesIO(pdf_file.read())
                        ).replace("\n", "")

                        self.assertRegex(document_text, r"CONTRACT")
                        self.assertRegex(document_text, r"DEFINITION")
                        self.assertRegex(
                            document_text, r"1 Rue de L'Exemple 75000, Paris."
                        )
