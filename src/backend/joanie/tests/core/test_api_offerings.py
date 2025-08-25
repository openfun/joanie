# pylint: disable=too-many-lines
"""Test suite for the offering API."""

import random
import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.core.utils import get_default_currency_symbol
from joanie.tests.base import BaseAPITestCase


class OfferingApiTest(BaseAPITestCase):
    """Test the API of the CourseProductRelation resource."""

    maxDiff = None

    def test_api_offering_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of offerings for
        anonymous users.
        """
        response = self.client.get("/api/v1.0/offerings/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_offering_read_list_without_accesses(self):
        """
        It should not be possible to retrieve the list of offerings for
        authenticated users without accesses.
        """
        factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/offerings/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "count": 0,
                "results": [],
                "previous": None,
                "next": None,
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_offering_read_list_with_accesses(self, _):
        """
        An authenticated user should be able to list all offerings
        related to courses for which it has accesses.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        courses = factories.CourseFactory.create_batch(2)
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            contract_definition=factories.ContractDefinitionFactory(),
            quote_definition=factories.QuoteDefinitionFactory(),
        )
        product.instructions = (
            "# An h1 header\n"
            "Paragraphs are separated by a blank line.\n"
            "2nd paragraph. *Italic*, **bold**, and `monospace`.\n"
            "Itemized lists look like:\n"
            "* this one\n"
            "* that one\n"
            "&gt; Block quotes\n"
            "## An h2 header\n"
            "1. first item\n"
            "2. second item\n"
        )
        product.save()
        course = courses[0]
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        factories.ProductFactory.create_batch(2)

        response = self.client.get(
            "/api/v1.0/offerings/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0],
            {
                "id": str(offering.id),
                "created_on": offering.created_on.isoformat().replace("+00:00", "Z"),
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                },
                "is_withdrawable": True,
                "product": {
                    "instructions": (
                        "<h1>An h1 header</h1>\n"
                        "<p>Paragraphs are separated by a blank line.\n"
                        "2nd paragraph. <em>Italic</em>, <strong>bold</strong>, "
                        "and <code>monospace</code>.\n"
                        "Itemized lists look like:\n"
                        "* this one\n"
                        "* that one\n"
                        "&gt; Block quotes</p>\n"
                        "<h2>An h2 header</h2>\n"
                        "<ol>\n"
                        "<li>first item</li>\n"
                        "<li>second item</li>\n"
                        "</ol>"
                    ),
                    "call_to_action": offering.product.call_to_action,
                    "certificate_definition": {
                        "description": offering.product.certificate_definition.description,
                        "name": offering.product.certificate_definition.name,
                        "title": offering.product.certificate_definition.title,
                    },
                    "contract_definition": {
                        "id": str(product.contract_definition.id),
                        "description": product.contract_definition.description,
                        "language": product.contract_definition.language,
                        "title": product.contract_definition.title,
                    },
                    "quote_definition": {
                        "id": str(product.quote_definition.id),
                        "title": product.quote_definition.title,
                        "description": product.quote_definition.description,
                        "name": product.quote_definition.name,
                        "language": product.quote_definition.language,
                        "body": product.quote_definition.body,
                    },
                    "state": {
                        "priority": product.state["priority"],
                        "datetime": product.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if product.state["datetime"]
                        else None,
                        "call_to_action": product.state["call_to_action"],
                        "text": product.state["text"],
                    },
                    "id": str(offering.product.id),
                    "price": float(offering.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organization": {
                                "id": str(target_course.organization.id),
                                "code": target_course.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": target_course.organization.title,
                            },
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
                                    "state": {
                                        "priority": course_run.state["priority"],
                                        "datetime": course_run.state["datetime"]
                                        .isoformat()
                                        .replace("+00:00", "Z"),
                                        "call_to_action": course_run.state[
                                            "call_to_action"
                                        ],
                                        "text": course_run.state["text"],
                                    },
                                    "start": course_run.start.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "end": course_run.end.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                }
                                for course_run in target_course.course_runs.all().order_by(
                                    "start"
                                )
                            ],
                            "position": target_course.offerings.get(
                                product=offering.product
                            ).position,
                            "is_graded": target_course.offerings.get(
                                product=offering.product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in offering.product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "title": offering.product.title,
                    "type": offering.product.type,
                },
                "organizations": [
                    {
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": "_this_field_is_mocked",
                        "title": organization.title,
                        "address": None,
                        "enterprise_code": organization.enterprise_code,
                        "activity_category_code": (organization.activity_category_code),
                        "contact_email": organization.contact_email,
                        "contact_phone": organization.contact_phone,
                        "dpo_email": organization.dpo_email,
                    }
                    for organization in offering.organizations.all()
                ],
            },
        )

    def test_api_offering_read_list_filtered_by_course_anonymous(self):
        """
        It should not be possible to list course's product offerings for
        anonymous users.
        """
        course = factories.CourseFactory()
        response = self.client.get(f"/api/v1.0/courses/{course.id}/products/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_offering_read_list_filtered_by_course_with_accesses(self, _):
        """
        An authenticated user should be able to list all course's product offerings
        for which it has accesses
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        courses = factories.CourseFactory.create_batch(2)
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)
        factories.OfferingFactory(
            product=factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
            ),
            course=courses[0],
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        factories.ProductFactory.create_batch(2)

        response = self.client.get(
            f"/api/v1.0/courses/{courses[0].id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)

    def test_api_offering_read_list_filtered_by_course_without_accesses(
        self,
    ):
        """
        It should not be possible to list course's product offerings for
        authenticated users without accesses.
        """
        factories.ProductFactory()
        course = factories.CourseFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content,
            {
                "count": 0,
                "results": [],
                "previous": None,
                "next": None,
            },
        )

    def test_api_offering_read_list_filtered_by_product_type(self):
        """
        An authenticated user should be able to list all course's product offerings
        filtered by product type.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            factories.OfferingFactory(
                product=factories.ProductFactory(type=product_type, courses=[]),
                course=access.course,
                organizations=factories.OrganizationFactory.create_batch(1),
            )

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 3)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            response = self.client.get(
                f"/api/v1.0/courses/{access.course.id}/products/?product_type={product_type}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 1)

        # Test with multiple product types
        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/"
            "?product_type=credential"
            "&product_type=certificate",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 2)

    def test_api_offering_read_list_filtered_by_invalid_product_type(
        self,
    ):
        """
        An authenticated user should be able to list all course's product offerings
        filtered by product type but if the type is invalid, it should
        return a 400.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/?product_type=invalid",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"product_type":['
            '"Select a valid choice. invalid is not one of the available choices."'
            "]}",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_offering_read_list_filtered_by_excluded_product_type(
        self,
    ):
        """
        An authenticated user should be able to list all course's product offerings
        filtered by excluding product type.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            factories.OfferingFactory(
                product=factories.ProductFactory(type=product_type, courses=[]),
                course=access.course,
                organizations=factories.OrganizationFactory.create_batch(1),
            )

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 3)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            response = self.client.get(
                f"/api/v1.0/courses/{access.course.id}/products/"
                f"?product_type_exclude={product_type}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 2)

        # Test with multiple excluded product types
        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/"
            "?product_type_exclude=credential"
            "&product_type_exclude=certificate",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)

    def test_api_offering_read_list_filtered_by_invalid_excluded_product_type(
        self,
    ):
        """
        An authenticated user should be able to list all course's product offerings
        filtered by excluded product type but if the type is invalid, it should
        return a 400.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)

        response = self.client.get(
            f"/api/v1.0/courses/{access.course.id}/products/?product_type_exclude=invalid",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"product_type_exclude":['
            '"Select a valid choice. invalid is not one of the available choices."'
            "]}",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_offering_read_detail_anonymous(self):
        """
        Anonymous users should not be able to retrieve a single offering through its id.
        """
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=courses
        )
        offering = models.CourseProductRelation.objects.get(
            course=courses[0], product=product
        )

        response = self.client.get(f"/api/v1.0/offerings/{offering.id}/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_offering_read_detail_anonymous_with_course_id(self):
        """
        Anonymous users should get a 404 when trying to retrieve a single offering
        through a course id and a product id that does not exist.
        """
        response = self.client.get(
            f"/api/v1.0/courses/{uuid.uuid4()}/products/{uuid.uuid4()}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_offering_read_detail_with_product_id_anonymous(self):
        """
        Anonymous users should be able to retrieve a single offering
        if a product id is provided.
        """
        course = factories.CourseFactory(code="00000")
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=factories.CourseFactory.create_batch(2),
        )
        offering = factories.OfferingFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with self.record_performance():
            self.client.get(f"/api/v1.0/courses/{course.code}/products/{product.id}/")

        # A second call to the url should benefit from caching on the product serializer
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(content["id"], str(offering.id))
        self.assertEqual(content["course"]["code"], "00000")
        self.assertEqual(content["product"]["id"], str(product.id))

        # This query should be cached
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Then cache should be language sensitive
        with self.record_performance():
            self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/",
                HTTP_ACCEPT_LANGUAGE="fr-fr",
            )

        with self.record_performance():
            self.client.get(
                f"/api/v1.0/courses/{course.code}/products/{product.id}/",
                HTTP_ACCEPT_LANGUAGE="fr-fr",
            )

    def test_api_offering_read_detail_no_organization(self):
        """
        An Offering without organizations should not be returned.
        """
        offering = factories.OfferingFactory(
            organizations=[],
        )

        # Anonymous user should not be able to retrieve this offering
        response = self.client.get(
            f"/api/v1.0/courses/{offering.course.id}/products/{offering.product.id}/",
        )
        self.assertContains(
            response,
            "No CourseProductRelation matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

        # Authenticated user with course access should not be able
        # to retrieve this offering
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserCourseAccessFactory(
            user=user,
            course=offering.course,
        )

        response = self.client.get(
            f"/api/v1.0/courses/{offering.course.id}/products/{offering.product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No CourseProductRelation matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No CourseProductRelation matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_offering_read_detail_without_accesses(self):
        """
        Authenticated users without course access should not be able to retrieve
        a single offering through its id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        offering = factories.OfferingFactory(course=course, product=product)

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_offering_read_detail_with_accesses(self, _):
        """
        Authenticated users with course access should be able to retrieve
        a single offering through its id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        quote_definition = factories.QuoteDefinitionFactory()
        offering = factories.OfferingFactory(
            course=course,
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__quote_definition=quote_definition,
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        with self.record_performance():
            self.client.get(
                f"/api/v1.0/offerings/{offering.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on the product serializer
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content,
            {
                "id": str(offering.id),
                "created_on": offering.created_on.isoformat().replace("+00:00", "Z"),
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                },
                "is_withdrawable": True,
                "product": {
                    "instructions": "",
                    "call_to_action": offering.product.call_to_action,
                    "certificate_definition": {
                        "description": offering.product.certificate_definition.description,
                        "name": offering.product.certificate_definition.name,
                        "title": offering.product.certificate_definition.title,
                    },
                    "contract_definition": {
                        "id": str(offering.product.contract_definition.id),
                        "description": offering.product.contract_definition.description,
                        "language": offering.product.contract_definition.language,
                        "title": offering.product.contract_definition.title,
                    },
                    "quote_definition": {
                        "id": str(offering.product.quote_definition.id),
                        "body": offering.product.quote_definition.body,
                        "description": offering.product.quote_definition.description,
                        "language": offering.product.quote_definition.language,
                        "name": offering.product.quote_definition.name,
                        "title": offering.product.quote_definition.title,
                    },
                    "state": {
                        "priority": offering.product.state["priority"],
                        "datetime": offering.product.state["datetime"]
                        .isoformat()
                        .replace("+00:00", "Z")
                        if offering.product.state["datetime"]
                        else None,
                        "call_to_action": offering.product.state["call_to_action"],
                        "text": offering.product.state["text"],
                    },
                    "id": str(offering.product.id),
                    "price": float(offering.product.price),
                    "price_currency": settings.DEFAULT_CURRENCY,
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
                                    "state": {
                                        "priority": course_run.state["priority"],
                                        "datetime": course_run.state["datetime"]
                                        .isoformat()
                                        .replace("+00:00", "Z"),
                                        "call_to_action": course_run.state[
                                            "call_to_action"
                                        ],
                                        "text": course_run.state["text"],
                                    },
                                    "start": course_run.start.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "end": course_run.end.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                }
                                for course_run in target_course.course_runs.all().order_by(
                                    "start"
                                )
                            ],
                            "position": target_course.offerings.get(
                                product=offering.product
                            ).position,
                            "is_graded": target_course.offerings.get(
                                product=offering.product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in offering.product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "title": offering.product.title,
                    "type": offering.product.type,
                },
                "organizations": [
                    {
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": "_this_field_is_mocked",
                        "title": organization.title,
                        "address": None,
                        "enterprise_code": organization.enterprise_code,
                        "activity_category_code": (organization.activity_category_code),
                        "contact_email": organization.contact_email,
                        "contact_phone": organization.contact_phone,
                        "dpo_email": organization.dpo_email,
                    }
                    for organization in offering.organizations.all()
                ],
                "rules": {
                    "discounted_price": None,
                    "discount_rate": None,
                    "discount_amount": None,
                    "discount_start": None,
                    "discount_end": None,
                    "description": None,
                    "nb_available_seats": None,
                    "has_seat_limit": False,
                    "has_seats_left": True,
                },
            },
        )

    def test_api_offering_read_offering_rules(self):
        """The detail of offer rules related to the product should be served as expected."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        product = offering.product
        course = offering.course
        factories.UserCourseAccessFactory(user=user, course=course)
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            nb_seats=random.randint(10, 100),
            discount=factories.DiscountFactory(amount=10),
        )
        for _ in range(3):
            factories.OrderFactory(
                course=course,
                product=product,
                offering_rules=[offering_rule],
                state=random.choice(enums.ORDER_STATES_BINDING),
            )
        for state, _label in enums.ORDER_STATE_CHOICES:
            if state in (*enums.ORDER_STATES_BINDING, enums.ORDER_STATE_TO_OWN):
                continue
            factories.OrderFactory(
                course=course,
                product=product,
                offering_rules=[offering_rule],
                state=state,
            )

        with self.record_performance():
            self.client.get(
                f"/api/v1.0/offerings/{offering.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on
        # the offering serializer
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": 90,
                "discount_amount": offering_rule.discount.amount,
                "discount_rate": offering_rule.discount.rate,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": offering_rule.available_seats,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_discount(self):
        """The discounted price should be calculated as expected."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        factories.UserCourseAccessFactory(user=user, course=offering.course)
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            nb_seats=random.randint(10, 100),
            discount=factories.DiscountFactory(amount=10),
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = response.json()
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            content["rules"],
            {
                "discounted_price": 90,
                "discount_amount": offering_rule.discount.amount,
                "discount_rate": offering_rule.discount.rate,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": offering_rule.available_seats,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_cache(self):
        """Cache should be reset on order submit and cancel."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        product = factories.ProductFactory(price="0.00")
        offering = factories.OfferingFactory(product=product)
        factories.UserCourseAccessFactory(user=user, course=offering.course)
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering, nb_seats=10
        )
        order = factories.OrderFactory(
            product=product, course=offering.course, offering_rules=[offering_rule]
        )

        self.client.get("/api/v1.0/offerings/", HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()

        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 10,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

        # Starting order state flow should impact the number of seat availabilities in the
        # representation of the product
        order.init_flow()

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 9,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

        # Cancelling order should re-credit the number of seat availabilities in the
        # representation of the product
        order.flow.cancel()

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 10,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_is_active(self):
        """
        Authenticated user should only have active offering rules on the course product
        offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()
        factories.UserCourseAccessFactory(user=user, course=offering.course)

        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering, is_active=True
        )
        factories.OfferingRuleFactory(course_product_relation=offering, is_active=False)
        factories.OfferingRuleFactory(course_product_relation=offering, is_active=True)
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            end="2025-02-16T16:35:49.326248Z",
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": offering_rule_1.available_seats,
                "has_seat_limit": False,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_assignable(self):
        """
        Authenticated user should only have assignable offer rules on the course product
        relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()
        factories.UserCourseAccessFactory(user=user, course=offering.course)

        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering, is_active=True, nb_seats=1
        )
        factories.OfferingRuleFactory(is_active=True, nb_seats=1)
        factories.OrderFactory(
            course=offering.course,
            product=offering.product,
            offering_rules=[offering_rule],
            state=enums.ORDER_STATE_PENDING_PAYMENT,
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 0,
                "has_seat_limit": True,
                "has_seats_left": False,
            },
        )

    def test_api_offering_read_offering_rules_no_seats_left_next_rule(self):
        """
        Authenticated user should only have assignable offer rules when on the course product
        relation it has 2 offers rules but one of them has no seat left.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        factories.UserCourseAccessFactory(user=user, course=offering.course)

        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=1,
            description="1 seat left",
            discount=factories.DiscountFactory(amount=10),
        )
        offering_rule_2 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=3,
            description="3 seats left",
            discount=factories.DiscountFactory(amount=30),
        )
        factories.OrderFactory(
            course=offering.course,
            product=offering.product,
            offering_rules=[offering_rule_1],
            state=enums.ORDER_STATE_PENDING_PAYMENT,
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": 70,
                "discount_amount": 30,
                "discount_rate": None,
                "description": "3 seats left",
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": offering_rule_2.available_seats,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_no_seats_left_regular_price(self):
        """
        Authenticated user should only have regular price when on the course product
        it has 1 offer with no seat left.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()
        factories.UserCourseAccessFactory(user=user, course=offering.course)

        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            nb_seats=1,
            description="1 seat left",
            discount=factories.DiscountFactory(amount=10),
        )
        factories.OrderFactory(
            course=offering.course,
            product=offering.product,
            offering_rules=[offering_rule_1],
            state=enums.ORDER_STATE_PENDING_PAYMENT,
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": None,
                "has_seat_limit": False,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_end_passed(self):
        """
        Offering rules with an end date that has passed should be ignored.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        factories.UserCourseAccessFactory(user=user, course=offering.course)

        now = timezone.now()
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            end=now - timedelta(hours=1),
            discount=factories.DiscountFactory(amount=30),
            description="expired 1 hour ago",
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            end=now - timedelta(minutes=1),
            discount=factories.DiscountFactory(amount=20),
            description="expired 1 minute ago",
        )
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            end=now + timedelta(minutes=1),
            discount=factories.DiscountFactory(amount=10),
            description="will expire in 1 minute",
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": 90,
                "discount_amount": offering_rule.discount.amount,
                "discount_rate": offering_rule.discount.rate,
                "description": offering_rule.description,
                "discount_start": None,
                "discount_end": offering_rule.end.isoformat().replace("+00:00", "Z"),
                "nb_available_seats": None,
                "has_seat_limit": False,
                "has_seats_left": True,
            },
        )

    def test_api_offering_read_offering_rules_mixed(self):
        """
        Offering rules with mixed states should return the expected values.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(product__price=100)
        factories.UserCourseAccessFactory(user=user, course=offering.course)

        now = timezone.now()
        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            description="A discount without seats left",
            nb_seats=1,
            discount=factories.DiscountFactory(amount=50),
        )
        factories.OrderFactory(
            course=offering.course,
            product=offering.product,
            offering_rules=[offering_rule_1],
            state=enums.ORDER_STATE_PENDING_PAYMENT,
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=False,
            description="An inactive discount",
            start=now - timedelta(days=1),
            end=now + timedelta(days=1),
            discount=factories.DiscountFactory(rate=0.1),
        )
        factories.OfferingRuleFactory(
            course_product_relation=offering,
            is_active=True,
            description="An expired discount with seats left",
            end=now - timedelta(minutes=1),
            discount=factories.DiscountFactory(rate=0.5),
            nb_seats=1,
        )

        response = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(
            content["rules"],
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": None,
                "has_seat_limit": False,
                "has_seats_left": True,
            },
        )

    def test_api_offering_create_anonymous(self):
        """
        Anonymous users should not be able to create an offering.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )

        response = self.client.post(
            "/api/v1.0/courses/products/",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_offering_create_authenticated(self):
        """
        Authenticated users should not be able to
        create an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )

        response = self.client.post(
            "/api/v1.0/courses/products/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_offering_create_with_accesses(self):
        """
        Authenticated users with course access should not be able
        to create an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_offering_update_anonymous(self):
        """
        Anonymous users should not be able to update an offering.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            data={
                "course_id": "abc",
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    def test_api_offering_update_authenticated(self):
        """
        Authenticated users without course access should not be able to
        update an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_offering_update_with_accesses(self):
        """
        Authenticated users with course access should not be able
        to update an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_offering_partially_update_anonymous(self):
        """
        Anonymous users should not be able to partially update an offering.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            data={
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    def test_api_offering_partially_update_authenticated(self):
        """
        Authenticated users without course access should not be able to
        partially update an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_offering_partially_update_with_accesses(self):
        """
        Authenticated users with course access should not be able to
        partially update an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.patch(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "product_id": "def",
            },
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_offering_delete_anonymous(self):
        """
        Anonymous users should not be able to delete an offering.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/"
        )

        self.assertContains(
            response,
            "Authentication credentials were not provided.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_offering_delete_authenticated(self):
        """
        Authenticated users without course access should not be able to
        delete an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_offering_delete_with_access(self):
        """
        Authenticated users with course access should not be able to
        delete an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[course]
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/products/{product.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_offering_read_list_filtered_by_product_title(self):
        """
        An authenticated user should be able to filter offering by
        product title.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)
        organization = factories.OrganizationFactory()
        product_1 = factories.ProductFactory(
            title="Introduction to resource filtering", courses=[]
        )
        product_2 = factories.ProductFactory(
            title="Advanced aerodynamic flows", courses=[]
        )
        product_3 = factories.ProductFactory(
            title="Rubber management on a single-seater", courses=[]
        )
        # Create translations title for products
        product_1.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de resource"
        )
        product_2.translations.create(
            language_code="fr-fr", title="Flux aérodynamiques avancés"
        )
        product_3.translations.create(
            language_code="fr-fr", title="Gestion d'une gomme sur une monoplace"
        )
        for product in [product_1, product_3]:
            factories.OfferingFactory(organizations=[organization], product=product)

        offering = factories.OfferingFactory(
            product=product_2,
            course=access.course,
            organizations=[organization],
        )

        # Prepare queries to test
        queries = [
            "Flux aérodynamiques avancés",
            "Flux+aérodynamiques+avancés",
            "aérodynamiques",
            "aerodynamic",
            "aéro",
            "aero",
            "aer",
            "advanced",
            "flows",
            "flo",
            "Advanced aerodynamic flows",
            "adv",
            "dynamic",
            "dyn",
            "ows",
            "av",
            "ux",
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/offerings/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 1)
            self.assertEqual(content["results"][0].get("id"), str(offering.id))

        # without parsing a query in parameter
        response = self.client.get(
            "/api/v1.0/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(offering.id))

        # with parsing a fake product title as query parameter
        response = self.client.get(
            "/api/v1.0/offerings/?query=veryFakeProductTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_offering_read_list_filtered_by_course_code(self):
        """
        An authenticated user should be able to filter offering by
        course code.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        course_1 = factories.CourseFactory(
            title="Introduction to resource filtering", code="MYCODE-0990"
        )
        course_2 = factories.CourseFactory(
            title="Advanced aerodynamic flows", code="MYCODE-0991"
        )
        course_3 = factories.CourseFactory(
            title="Rubber management on a single-seater", code="MYCODE-0992"
        )
        access = factories.UserCourseAccessFactory(user=user, course=course_2)
        offering = factories.OfferingFactory(
            course=access.course,
            organizations=[organization],
        )
        for course in [course_1, course_3]:
            factories.OfferingFactory(organizations=[organization], course=course)

        response = self.client.get(
            f"/api/v1.0/offerings/?query={access.course.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0].get("id"), str(offering.id))

        response = self.client.get(
            f"/api/v1.0/offerings/?query={access.course.code[:1]}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0].get("id"), str(offering.id))

        # without parsing a query parameter I should see my offering
        response = self.client.get(
            "/api/v1.0/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0].get("id"), str(offering.id))

        # with parsing a fake product title as query parameter
        response = self.client.get(
            "/api/v1.0/offerings/?query=veryFakeCourseCode",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_offering_read_list_filtered_by_organization_title(self):
        """
        An authenticated user should be able to filter offering by
        organization title when they have access to the course.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        access = factories.UserCourseAccessFactory(user=user)
        organization_1 = factories.OrganizationFactory(title="Organization alpha 01")
        organization_2 = factories.OrganizationFactory(title="Organization beta 02")
        organization_3 = factories.OrganizationFactory(title="Organization kappa 03")
        organization_4 = factories.OrganizationFactory(title="Organization gamma 04")
        for organization in [organization_1, organization_2, organization_3]:
            factories.OfferingFactory(organizations=[organization])
        offering = factories.OfferingFactory(
            course=access.course,
            organizations=[organization_4],
        )

        # Prepare queries to test
        queries = [
            "amma",
            "gamma",
            "mm",
            "or",
            "organ",
            "organization",
            "organization g",
            "organization+ga",
            "organization gamma",
            "04",
            "ma 04",
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/offerings/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(len(content["results"]), 1)
            self.assertEqual(content["results"][0].get("id"), str(offering.id))

        # without parsing a query in parameter
        response = self.client.get(
            "/api/v1.0/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(offering.id))

        # with parsing a fake product title as query parameter
        response = self.client.get(
            "/api/v1.0/offerings/?query=veryFakeOrganizationTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
            10: (30, 45, 45),
            100: (20, 30, 30, 20),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_plan_with_product_id(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule for
        a single offering if a product id is provided
        and the product is a credential. If there are archived course runs, they should be ignored.
        """
        mocked_now = datetime(2024, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        # Create an archived course_run
        factories.CourseRunFactory(
            start=datetime(2023, 12, 15, tzinfo=ZoneInfo("UTC")),
            end=datetime(2023, 12, 31, tzinfo=ZoneInfo("UTC")),
            course=course,
        )

        product = factories.ProductFactory(
            price=3,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "price": 3.00,
                "discount": None,
                "discounted_price": None,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 0.90,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 2.10,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2024-03-01",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
            10: (30, 45, 45),
            100: (20, 30, 30, 20),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_plan_with_product_id_discount(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule
        with applied discount for a single offering
        if a product id is provided and the product is a credential.
        If there are archived course runs, they should be ignored.
        """
        mocked_now = datetime(2024, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        # Create an archived course_run
        factories.CourseRunFactory(
            start=datetime(2023, 12, 15, tzinfo=ZoneInfo("UTC")),
            end=datetime(2023, 12, 31, tzinfo=ZoneInfo("UTC")),
            course=course,
        )

        product = factories.ProductFactory(
            price=3,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = factories.OfferingRuleFactory(
            discount=factories.DiscountFactory(rate=0.50),
        )
        offering.offering_rules.add(offering_rule)

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "price": 3.00,
                "discount": "-50%",
                "discounted_price": 1.50,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 0.45,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 1.05,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2024-03-01",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (100,),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_plan_with_certificate_product_id(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule for
        a single offering if a product id is provided
        and the product is a certificate.
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        product = factories.ProductFactory(
            price=3,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "price": 3.00,
                "discount": None,
                "discounted_price": None,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 3.00,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (100,),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_plan_with_certificate_product_id_discount(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule
        with applied discount for a single offering
        if a product id is provided and the product is a certificate.
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2024, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        product = factories.ProductFactory(
            price=3,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = factories.OfferingRuleFactory(
            discount=factories.DiscountFactory(rate=0.50),
        )
        offering.offering_rules.add(offering_rule)

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2024, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "price": 3.00,
                "discount": "-50%",
                "discounted_price": 1.50,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 1.50,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())

    def test_api_offering_voucher_payment_plan_authenticated_invalid_voucher(
        self,
    ):
        """
        Authenticated users should not be able to retrieve a payment schedule and the estimated
        discounted price with an invalid voucher code.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory()

        response = self.client.get(
            f"/api/v1.0/courses/{offering.course.code}/"
            f"products/{offering.product.id}/payment-plan/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"voucher_code": "invalid_code"},
        )
        response_relation_path = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/payment-plan/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"voucher_code": "invalid_code"},
        )
        response_with_query_params = self.client.get(
            f"/api/v1.0/courses/{offering.course.code}/"
            f"products/{offering.product.id}/payment-plan/?voucher_code=invalid_code",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        response_relation_path_with_query_param = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/payment-plan/?voucher_code=invalid_code",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())
        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.NOT_FOUND, response.json()
        )
        self.assertEqual(
            response_with_query_params.status_code,
            HTTPStatus.NOT_FOUND,
            response.json(),
        )
        self.assertEqual(
            response_relation_path_with_query_param.status_code,
            HTTPStatus.NOT_FOUND,
            response.json(),
        )

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            10: (30, 70),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_voucher_payment_plan_anonymous(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule and the estimated
        discounted price with a voucher code.
        """
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        # Create an archived course_run
        factories.CourseRunFactory(
            start=datetime(2025, 12, 15, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 12, 31, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        product = factories.ProductFactory(
            price=10,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        voucher = factories.VoucherFactory(discount=factories.DiscountFactory(rate=0.1))

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{offering.course.code}/"
                f"products/{offering.product.id}/payment-plan/",
                data={"voucher_code": voucher.code},
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/",
                data={"voucher_code": voucher.code},
            )
            response_with_query_params = self.client.get(
                f"/api/v1.0/courses/{offering.course.code}/"
                f"products/{offering.product.id}/payment-plan/?voucher_code={voucher.code}",
            )
            response_relation_with_query_params = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/?voucher_code={voucher.code}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(
            response.json(),
            {
                "price": 10.00,
                "discount": "-10%",
                "discounted_price": 9.00,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 2.70,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2025-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 6.30,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2025-03-01",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )
        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(response_relation_path.json(), response.json())
        self.assertEqual(
            response_with_query_params.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(response_with_query_params.json(), response.json())
        self.assertEqual(
            response_relation_with_query_params.status_code,
            HTTPStatus.OK,
            response.json(),
        )
        self.assertEqual(response_relation_with_query_params.json(), response.json())

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            10: (30, 70),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_voucher_payment_plan_with_credential_product_id_with_voucher_code(
        self,
    ):
        """
        Authenticated users should be able to retrieve a payment schedule with the estimated
        discounted price of a voucher code for a single offering if a product id is provided
        and the product is a credential. If there are archived course runs, they should be ignored.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        mocked_now = datetime(2025, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        # Create an archived course_run
        factories.CourseRunFactory(
            start=datetime(2024, 12, 15, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC")),
            course=course,
        )

        product = factories.ProductFactory(
            price=10,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
        )
        voucher = factories.VoucherFactory(
            multiple_use=True,
            multiple_users=True,
            discount=factories.DiscountFactory(amount=1),
        )
        payload = {"voucher_code": voucher.code}

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=payload,
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=payload,
            )
            response_with_query_params = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/?voucher_code={voucher.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            response_relation_path_with_query_param = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/"
                f"?voucher_code={voucher.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "price": 10.00,
                "discount": f"-1 {get_default_currency_symbol()}",
                "discounted_price": 9.00,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 2.70,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2025-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 6.30,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2025-03-01",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )
        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(response_relation_path.json(), response.json())
        self.assertEqual(
            response_with_query_params.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(response_with_query_params.json(), response.json())
        self.assertEqual(
            response_relation_path_with_query_param.status_code,
            HTTPStatus.OK,
            response.json(),
        )
        self.assertEqual(
            response_relation_path_with_query_param.json(), response.json()
        )

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            100: (100,),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_voucher_payment_plan_with_certificate_product_id_with_voucher_code(
        self,
    ):
        """
        Authenticated users should be able to retrieve a payment schedule for
        a single offering if a product id is provided and the product is a certificate.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        product = factories.ProductFactory(
            price=100,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
        )
        voucher = factories.VoucherFactory(
            multiple_use=True,
            multiple_users=True,
            discount=factories.DiscountFactory(rate=0.1),
        )
        payload = {"voucher_code": voucher.code}

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=payload,
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
                data=payload,
            )
            response_with_query_params = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-plan/?voucher_code={voucher.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            response_relation_path_with_query_param = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-plan/"
                f"?voucher_code={voucher.code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "price": 100.00,
                "discount": "-10%",
                "discounted_price": 90.00,
                "payment_schedule": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "amount": 90.00,
                        "currency": settings.DEFAULT_CURRENCY,
                        "due_date": "2025-01-17",
                        "state": enums.PAYMENT_STATE_PENDING,
                    },
                ],
            },
        )

        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(response_relation_path.json(), response.json())
        self.assertEqual(
            response_with_query_params.status_code, HTTPStatus.OK, response.json()
        )
        self.assertEqual(response_with_query_params.json(), response.json())
        self.assertEqual(
            response_relation_path_with_query_param.status_code,
            HTTPStatus.OK,
            response.json(),
        )
        self.assertEqual(
            response_relation_path_with_query_param.json(), response.json()
        )

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            100: (100,),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_schedule_anonymous_product_type_certificate(self):
        """
        Anonymous user should be able to get the payment schedule of an offering
        for a certificate product.
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        product = factories.ProductFactory(
            price=100,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
        )

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-schedule/",
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-schedule/",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 100.00,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.OK, response.json()
        )

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            100: (30, 35, 35),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_schedule_anonymous_product_type_credential(self):
        """
        Anonymous user should be able to get the payment schedule of an offering for a
        credential product
        """
        mocked_now = datetime(2025, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        # Create an archived course_run
        factories.CourseRunFactory(
            start=datetime(2024, 12, 15, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC")),
            course=course,
        )

        product = factories.ProductFactory(
            price=100,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
        )

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-schedule/",
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-schedule/",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 30.00,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 35.00,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-03-01",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 35.00,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-04-01",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        self.assertEqual(
            response_relation_path.status_code, HTTPStatus.OK, response.json()
        )

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            100: (100,),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_schedule_anonymous_with_certificate_product_id_discount(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule
        with applied discount for a single offering
        """
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
        )
        product = factories.ProductFactory(
            price=100,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = factories.OfferingRuleFactory(
            discount=factories.DiscountFactory(rate=0.50),
        )
        offering.offering_rules.add(offering_rule)

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch(
                "django.utils.timezone.now",
                return_value=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            ),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-schedule/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-schedule/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 50.00,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())

    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            5: (30, 70),
        },
        DEFAULT_CURRENCY="EUR",
    )
    def test_api_offering_payment_schedule_with_product_id_credential_discount(
        self,
    ):
        """
        Anonymous users should be able to retrieve a payment schedule with applied discount for
        a single offering when the product is credential. Archived ones should be ignored.
        """
        mocked_now = datetime(2025, 1, 1, 0, tzinfo=ZoneInfo("UTC"))
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_start=datetime(2025, 1, 1, 14, tzinfo=ZoneInfo("UTC")),
            start=datetime(2025, 3, 1, 14, tzinfo=ZoneInfo("UTC")),
            end=datetime(2025, 5, 1, 14, tzinfo=ZoneInfo("UTC")),
            course=course,
        )
        # Create an archived course_run
        factories.CourseRunFactory(
            start=datetime(2024, 12, 15, tzinfo=ZoneInfo("UTC")),
            end=datetime(2024, 12, 31, tzinfo=ZoneInfo("UTC")),
            course=course,
        )

        product = factories.ProductFactory(
            price=3,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        offering = factories.OfferingFactory(
            course=course_run.course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        offering_rule = factories.OfferingRuleFactory(
            discount=factories.DiscountFactory(rate=0.50),
        )
        offering.offering_rules.add(offering_rule)

        with (
            mock.patch("uuid.uuid4", return_value=uuid.UUID(int=1)),
            mock.patch("django.utils.timezone.now", return_value=mocked_now),
        ):
            response = self.client.get(
                f"/api/v1.0/courses/{course_run.course.code}/"
                f"products/{product.id}/payment-schedule/"
            )
            response_relation_path = self.client.get(
                f"/api/v1.0/offerings/{offering.id}/payment-schedule/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 0.45,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "amount": 1.05,
                    "currency": settings.DEFAULT_CURRENCY,
                    "due_date": "2025-03-01",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        self.assertEqual(response_relation_path.status_code, HTTPStatus.OK)
        self.assertEqual(response_relation_path.json(), response.json())

    def test_api_offering_get_organizations_not_authenticated(self):
        """
        Unauthenticated user should not be able to get the list of organizations that
        delivers the offering.
        """
        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            organizations=[organization_1, organization_2]
        )

        response = self.client.get(
            f"/api/v1.0/courses/{offering.course.code}/"
            f"products/{offering.product.id}/get-organizations/",
        )
        response_relation_path = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/get-organizations/"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())
        self.assertEqual(
            response_relation_path.status_code,
            HTTPStatus.UNAUTHORIZED,
            response_relation_path.json(),
        )

    def test_api_offering_get_organizations_invalid_offering_id(self):
        """
        Authenticated user should get an error if passing an invalid id for the offering
        to get the list of organizations.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/courses/invalid_id/products/invalid_id/get-organizations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        response_relation_path = self.client.get(
            "/api/v1.0/offerings/invalid_id/get-organizations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())
        self.assertEqual(
            response_relation_path.status_code,
            HTTPStatus.NOT_FOUND,
            response_relation_path.json(),
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_offering_get_organizations(self, _):
        """
        Authenticated user should be able to get the list of organizations that
        delivers the offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            organizations=[organization_1, organization_2]
        )

        response = self.client.get(
            f"/api/v1.0/courses/{offering.course.code}/"
            f"products/{offering.product.id}/get-organizations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        response_relation_path = self.client.get(
            f"/api/v1.0/offerings/{offering.id}/get-organizations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK, response.json())
        self.assertEqual(
            response.json(),
            [
                {
                    "code": organization.code,
                    "id": str(organization.id),
                    "logo": "_this_field_is_mocked",
                    "title": organization.title,
                    "address": None,
                    "enterprise_code": organization.enterprise_code,
                    "activity_category_code": (organization.activity_category_code),
                    "contact_email": organization.contact_email,
                    "contact_phone": organization.contact_phone,
                    "dpo_email": organization.dpo_email,
                }
                for organization in offering.organizations.all()
            ],
        )
        self.assertEqual(
            response_relation_path.status_code,
            HTTPStatus.OK,
            response_relation_path.json(),
        )
        self.assertEqual(response.json(), response_relation_path.json())
