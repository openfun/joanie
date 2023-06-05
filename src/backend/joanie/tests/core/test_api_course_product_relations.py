"""Test suite for the Course Product Relation API."""
from unittest import mock

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class CourseProductRelationApiTest(BaseAPITestCase):
    """Test the API of the CourseProductRelation resource."""

    def test_api_course_product_relation_read_list_anonymous(self):
        """
        It should not be possible to retrieve the list of course product relations for
        anonymous users.
        """
        response = self.client.get("/api/v1.0/course-product-relations/")

        self.assertEqual(response.status_code, 401)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_product_relation_read_list_without_accesses(self):
        """
        It should not be possible to retrieve the list of course product relations for
        authenticated users without accesses.
        """
        factories.ProductFactory()
        user = factories.UserFactory.build()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/course-product-relations/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

        self.assertEqual(response.status_code, 200)
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
    def test_api_course_product_relation_read_list_with_accesses(self, _):
        """
        An authenticated user should be able to list all course product relations
        related to courses for which it has accesses.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        courses = factories.CourseFactory.create_batch(2)
        for course in courses:
            factories.UserCourseAccessFactory(user=user, course=course)
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        course = courses[0]
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        factories.ProductFactory.create_batch(2)

        with self.assertNumQueries(14):
            response = self.client.get(
                "/api/v1.0/course-product-relations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(
            content["results"][0],
            {
                "created_on": relation.created_on.isoformat().replace("+00:00", "Z"),
                "course": {
                    "created_on": course.created_on.isoformat().replace("+00:00", "Z"),
                    "abilities": course.get_abilities(user),
                    "code": course.code,
                    "id": str(course.id),
                    "cover": "_this_field_is_mocked",
                    "title": course.title,
                    "organizations": [
                        {
                            "code": organization.code,
                            "id": str(organization.id),
                            "logo": "_this_field_is_mocked",
                            "title": organization.title,
                        }
                        for organization in course.organizations.all()
                    ],
                    "selling_organizations": [
                        {
                            "id": str(organization.id),
                            "code": organization.code,
                            "logo": "_this_field_is_mocked",
                            "title": organization.title,
                        }
                        for organization in relation.organizations.all()
                    ],
                    "products": [str(product.id) for product in course.products.all()],
                    "course_runs": [
                        str(course_run.id) for course_run in course.course_runs.all()
                    ],
                    "state": dict(course.state),
                },
                "product": {
                    "call_to_action": relation.product.call_to_action,
                    "certificate_definition": {
                        "description": relation.product.certificate_definition.description,
                        "name": relation.product.certificate_definition.name,
                        "title": relation.product.certificate_definition.title,
                    },
                    "organizations": [],
                    "id": str(relation.product.id),
                    "price": float(relation.product.price.amount),
                    "price_currency": str(relation.product.price.currency),
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
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                        "+00:00",
                                        "Z",
                                    ),
                                }
                                for course_run in target_course.course_runs.all().order_by(
                                    "start"
                                )
                            ],
                            "position": target_course.product_relations.get(
                                product=relation.product
                            ).position,
                            "is_graded": target_course.product_relations.get(
                                product=relation.product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in relation.product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "title": relation.product.title,
                    "type": relation.product.type,
                    "orders": [],
                },
            },
        )

    def test_api_course_product_relation_read_detail_anonymous(self):
        """
        Anonymous users should not be able to retrieve a single course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.get(f"/api/v1.0/course-product-relations/{relation.id}/")

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_read_detail_authenticated(self):
        """
        Authenticated users without course access should not be able to
        retrieve a single course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_read_detail_with_accesses(self):
        """
        Authenticated users with course access should not be able to retrieve
        a single course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.get(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_create_anonymous(self):
        """
        Anonymous users should not be able to create a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )

        response = self.client.post(
            "/api/v1.0/course-product-relations/",
            data={
                "course": str(course.id),
                "product": str(product.id),
            },
        )

        self.assertEqual(response.status_code, 401)
        content = response.json()
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_course_product_relation_create_authenticated(self):
        """
        Authenticated users should not be able to
        create a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )

        response = self.client.post(
            "/api/v1.0/course-product-relations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course": str(course.id),
                "product": str(product.id),
            },
        )

        self.assertContains(response, 'Method \\"POST\\" not allowed.', status_code=405)
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_course_product_relation_update_anonymous(self):
        """
        Anonymous users should not be able to update a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.put(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            data={
                "course": "abc",
                "product": "def",
            },
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_update_authenticated(self):
        """
        Authenticated users without course access should not be able to
        update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.put(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course": str(course.id),
                "product": str(product.id),
            },
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_update_with_accesses(self):
        """
        Authenticated users with course access should not be able
        to update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.put(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course": str(course.id),
                "product": str(product.id),
            },
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_partially_update_anonymous(self):
        """
        Anonymous users should not be able to partially update a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.patch(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            data={
                "product": "def",
            },
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_partially_update_authenticated(self):
        """
        Authenticated users without course access should not be able to
        partially update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.patch(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "product": "def",
            },
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_partially_update_with_accesses(self):
        """
        Authenticated users with course access should not be able to
        partially update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.patch(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "product": "def",
            },
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_product_relation_delete_anonymous(self):
        """
        Anonymous users should not be able to delete a course product relation.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.delete(
            f"/api/v1.0/course-product-relations/{relation.id}/"
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_course_product_relation_delete_authenticated(self):
        """
        Authenticated users without course access should not be able to
        delete a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )

        response = self.client.delete(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)

    def test_api_course_product_relation_delete_with_access(self):
        """
        Authenticated users with course access should not be able to
        delete a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[]
        )
        relation = factories.CourseProductRelationFactory(
            course=course, product=product
        )
        factories.UserCourseAccessFactory(user=user, course=course)

        response = self.client.delete(
            f"/api/v1.0/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )
        self.assertEqual(models.CourseProductRelation.objects.count(), 1)
