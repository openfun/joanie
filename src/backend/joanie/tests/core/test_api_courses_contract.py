# pylint: disable=duplicate-code
"""Test suite for the Courses Contract API"""

from http import HTTPStatus
from unittest import mock

from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseContractApiTest(BaseAPITestCase):
    """Tests for the Courses Contract API"""

    maxDiff = None

    def test_api_courses_contracts_list_anonymous(self):
        """Anonymous user cannot query all contracts from a course."""
        course = factories.CourseFactory()

        with self.record_performance():
            response = self.client.get(f"/api/v1.0/courses/{str(course.id)}/contracts/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_courses_contracts_list_without_access(self):
        """
        Authenticated user without access to the course organization cannot query
        organization's contracts for a course.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory.create_batch(
            5,
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(offering.course.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_courses_contracts_list_with_accesses(self, _):
        """
        Authenticated user with any access to the organization
        can query organization's course contracts.
        """
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(2)
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # - Create contracts for two organizations with access
        #   and several courses.
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user,
                organization=organization,
            )

            for course in courses:
                offering = factories.OfferingFactory(
                    organizations=[organization],
                    course=course,
                    product__contract_definition=factories.ContractDefinitionFactory(),
                )
                factories.ContractFactory.create_batch(
                    5,
                    order__product=offering.product,
                    order__course=course,
                    order__organization=organization,
                )
                # Canceled orders should be excluded
                factories.ContractFactory.create_batch(
                    2,
                    order__product=offering.product,
                    order__course=course,
                    order__organization=organization,
                    order__state=enums.ORDER_STATE_CANCELED,
                )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)
        factories.ContractFactory(order__owner=user)

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(courses[0].id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        contracts = models.Contract.objects.filter(
            order__course=courses[0],
            order__state=enums.ORDER_STATE_COMPLETED,
        )
        expected_contracts = sorted(contracts, key=lambda x: x.created_on, reverse=True)
        assert response.json() == {
            "count": 10,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": str(contract.id),
                    "abilities": {
                        "sign": contract.get_abilities(user)["sign"],
                    },
                    "created_on": contract.created_on.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "student_signed_on": contract.student_signed_on.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if contract.student_signed_on
                    else None,
                    "organization_signatory": None,
                    "organization_signed_on": contract.organization_signed_on.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if contract.organization_signed_on
                    else None,
                    "definition": {
                        "description": contract.definition.description,
                        "id": str(contract.definition.id),
                        "language": contract.definition.language,
                        "title": contract.definition.title,
                    },
                    "order": {
                        "id": str(contract.order.id),
                        "state": contract.order.state,
                        "course": {
                            "code": contract.order.course.code,
                            "cover": "_this_field_is_mocked",
                            "id": str(contract.order.course.id),
                            "title": contract.order.course.title,
                        },
                        "enrollment": None,
                        "organization": {
                            "id": str(contract.order.organization.id),
                            "code": contract.order.organization.code,
                            "logo": "_this_field_is_mocked",
                            "title": contract.order.organization.title,
                            "address": None,
                            "enterprise_code": contract.order.organization.enterprise_code,
                            "activity_category_code": (
                                contract.order.organization.activity_category_code
                            ),
                            "contact_email": contract.order.organization.contact_email,
                            "contact_phone": contract.order.organization.contact_phone,
                            "dpo_email": contract.order.organization.dpo_email,
                        },
                        "owner_name": contract.order.owner.get_full_name(),
                        "product_title": contract.order.product.title,
                    },
                }
                for contract in expected_contracts
            ],
        }

    def test_api_courses_contracts_list_filter_signature_state(self):
        """
        Authenticated user with any access to the organization
        can query organization's course contracts and filter them by signature state.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        unsigned_contracts = factories.ContractFactory.create_batch(
            5,
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        half_signed_contract = factories.ContractFactory.create_batch(
            3,
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        signed_contract = factories.ContractFactory.create(
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)
        factories.ContractFactory(order__owner=user)

        # - List without filter should return 9 contracts
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(offering.course.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 9)

        # - Filter by state=unsigned should return 5 contracts
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(offering.course.id)}/contracts/?signature_state=unsigned",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 5)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in unsigned_contracts]
        )

        # - Filter by state=half_signed should return 3 contracts
        with self.record_performance():
            response = self.client.get(
                (
                    f"/api/v1.0/courses/{str(offering.course.id)}"
                    "/contracts/?signature_state=half_signed"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 3)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in half_signed_contract]
        )

        # - Filter by state=signed should return 1 contract
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(offering.course.id)}/contracts/?signature_state=signed",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertEqual(result_ids, [str(signed_contract.id)])

    def test_api_courses_contracts_list_filter_by_offering_id(self):
        """
        Authenticated user with any access to the organization can query organization's
        course contracts and filter them by offering.
        """
        organization = factories.OrganizationFactory.create()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(user=user, organization=organization)
        course = factories.CourseFactory()
        other_organization = factories.OrganizationFactory.create()

        offering_1 = factories.OfferingFactory(
            organizations=[organization, other_organization],
            course=course,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        offering_2 = factories.OfferingFactory(
            course=course,
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        contracts_1 = factories.ContractFactory.create_batch(
            5,
            order__product=offering_1.product,
            order__course=offering_1.course,
            order__organization=organization,
        )

        contracts_2 = factories.ContractFactory.create_batch(
            3,
            order__product=offering_2.product,
            order__course=offering_2.course,
            order__organization=organization,
        )

        # Create random contracts that should not be returned
        other_offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory.create(
            order__product=offering_1.product,
            order__course=offering_1.course,
            order__organization=other_organization,
        )

        factories.ContractFactory.create_batch(
            3,
            order__product=other_offering.product,
            order__course=other_offering.course,
            order__organization=organization,
        )

        factories.ContractFactory.create_batch(8)
        factories.ContractFactory(order__owner=user)

        # - List without filter should return 8 contracts
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 8)

        # - Filter by the first offering should return 5 contracts
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/contracts/?offering_id={offering_1.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 5)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in contracts_1]
        )

        # - Filter by the second offering should return 3 contracts
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/contracts/?offering_id={offering_2.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 3)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in contracts_2]
        )

        # - Filter by the other offering should return no contracts
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.id}/contracts/?offering_id={other_offering.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        self.assertEqual(count, 0)

    def test_api_courses_contracts_retrieve_anonymous(self):
        """
        Anonymous user cannot query an organization's course contract.
        """
        contract = factories.ContractFactory()
        course = contract.order.course

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_courses_contracts_retrieve_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        an organization's course contract.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        # Having course access does not imply to be able to access to course's contract
        factories.UserCourseAccessFactory(course=offering.course, user=user)

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(organization.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_courses_contracts_retrieve_with_accesses(self, _):
        """
        Authenticated user with any access to the organization
        can query an organization's course contract.
        """
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(2)
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # - Create contracts for two organizations with accesses, and several courses
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            for course in courses:
                offering = factories.OfferingFactory(
                    organizations=[organization],
                    course=course,
                    product__contract_definition=factories.ContractDefinitionFactory(),
                )
                factories.ContractFactory.create_batch(
                    5,
                    order__product=offering.product,
                    order__course=course,
                    order__organization=organization,
                )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)
        factories.ContractFactory(order__owner=user)

        contract = models.Contract.objects.filter(order__course=courses[0]).first()

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(courses[0].id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        assert response.json() == {
            "id": str(contract.id),
            "abilities": {
                "sign": contract.get_abilities(user)["sign"],
            },
            "created_on": contract.created_on.isoformat().replace("+00:00", "Z"),
            "student_signed_on": contract.student_signed_on.isoformat().replace(
                "+00:00", "Z"
            )
            if contract.student_signed_on
            else None,
            "organization_signatory": None,
            "organization_signed_on": contract.organization_signed_on.isoformat().replace(
                "+00:00", "Z"
            )
            if contract.organization_signed_on
            else None,
            "definition": {
                "description": contract.definition.description,
                "id": str(contract.definition.id),
                "language": contract.definition.language,
                "title": contract.definition.title,
            },
            "order": {
                "id": str(contract.order.id),
                "state": contract.order.state,
                "course": {
                    "code": contract.order.course.code,
                    "cover": "_this_field_is_mocked",
                    "id": str(contract.order.course.id),
                    "title": contract.order.course.title,
                },
                "enrollment": None,
                "organization": {
                    "id": str(contract.order.organization.id),
                    "code": contract.order.organization.code,
                    "logo": "_this_field_is_mocked",
                    "title": contract.order.organization.title,
                    "address": None,
                    "enterprise_code": contract.order.organization.enterprise_code,
                    "activity_category_code": (
                        contract.order.organization.activity_category_code
                    ),
                    "contact_email": contract.order.organization.contact_email,
                    "contact_phone": contract.order.organization.contact_phone,
                    "dpo_email": contract.order.organization.dpo_email,
                },
                "owner_name": contract.order.owner.get_full_name(),
                "product_title": contract.order.product.title,
            },
        }

    def test_api_courses_contracts_retrieve_with_accesses_and_canceled_order(self):
        """
        Authenticated user with any access to the organization
        can query an organization's course contract if the related order is validated.
        """
        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(2)
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # - Create contracts for two organizations with accesses, and several courses
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            for course in courses:
                offering = factories.OfferingFactory(
                    organizations=[organization],
                    course=course,
                    product__contract_definition=factories.ContractDefinitionFactory(),
                )
                factories.ContractFactory.create_batch(
                    5,
                    order__product=offering.product,
                    order__course=course,
                    order__organization=organization,
                    order__state=enums.ORDER_STATE_CANCELED,
                )

        contract = models.Contract.objects.filter(order__course=courses[0]).first()

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{str(courses[0].id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            "No Contract matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_courses_contracts_retrieve_with_accesses_and_course_code(self):
        """
        Authenticated user with any access to the organization
        can query an organization's course contract. Furthermore, the api endpoint
        should work with the course code instead of the course id.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{offering.course.code}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(response, str(contract.id), status_code=HTTPStatus.OK)

    def test_api_courses_contracts_create_anonymous(self):
        """Anonymous user cannot create an organization's contract."""
        course = factories.CourseFactory()

        with self.record_performance():
            response = self.client.post(
                f"/api/v1.0/courses/{str(course.id)}/contracts/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_courses_contracts_create_authenticated(self):
        """Authenticated user cannot create an organization's contract."""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.record_performance():
            response = self.client.post(
                f"/api/v1.0/courses/{str(course.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_contracts_update_anonymous(self):
        """Anonymous user cannot update an organization's contract."""
        contract = factories.ContractFactory()
        course = contract.order.course

        with self.record_performance():
            response = self.client.put(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_courses_contracts_update_authenticated(self):
        """Authenticated user cannot update an organization's contract."""
        contract = factories.ContractFactory()
        course = contract.order.course
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.record_performance():
            response = self.client.put(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_contracts_patch_anonymous(self):
        """Anonymous user cannot patch an organization's contract."""
        contract = factories.ContractFactory()
        course = contract.order.course

        with self.record_performance():
            response = self.client.patch(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_courses_contracts_patch_authenticated(self):
        """Authenticated user cannot patch an organization's contract."""
        contract = factories.ContractFactory()
        course = contract.order.course
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.record_performance():
            response = self.client.patch(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_courses_contracts_delete_anonymous(self):
        """Anonymous user cannot delete an organization's contract."""
        contract = factories.ContractFactory()
        course = contract.order.course

        with self.record_performance():
            response = self.client.delete(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_courses_contracts_delete_authenticated(self):
        """Authenticated user cannot delete an organization's contract."""
        contract = factories.ContractFactory()
        course = contract.order.course
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.record_performance():
            response = self.client.delete(
                f"/api/v1.0/courses/{str(course.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
