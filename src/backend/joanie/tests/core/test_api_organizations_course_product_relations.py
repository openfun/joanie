"""
Test suite for Organization's CourseProductRelation API endpoint.
"""

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationCourseProductRelationApiTest(BaseAPITestCase):
    """
    Test suite for Organization's CourseProductRelation API endpoint.
    """

    def test_api_organizations_course_product_relations_read_list_anonymous(self):
        """
        Anonymous user cannot query all CourseProductRelation form an organization
        """

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)
        factories.UserOrganizationAccessFactory(organization=organizations[0])
        relations = []
        for course, product in zip(courses, products):
            relations.append(
                factories.CourseProductRelationFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/course-product-relations/",
            )

        self.assertEqual(response.status_code, 401)

    def test_api_organizations_course_product_relations_read_list_with_accesses(self):
        """
        Get all CourseProductRelation from an organization
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)
        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )
        relations = []
        for course, product in zip(courses, products):
            relations.append(
                factories.CourseProductRelationFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(53):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/course-product-relations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 5)
        self.assertEqual(
            set(map(lambda x: str(x["id"]), content["results"])),
            set(map(lambda x: str(x.id), relations)),
        )

    def test_api_organizations_course_product_relations_read_list_without_access(self):
        """
        Cannot get all CourseProductRelation from an organization without access
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)

        relations = []
        for course, product in zip(courses, products):
            relations.append(
                factories.CourseProductRelationFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/course-product-relations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_organizations_course_product_relations_read_details_anonymous(self):
        """
        Anonymous user cannot query a single CourseProductRelation form an organization
        """

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)
        factories.UserOrganizationAccessFactory(organization=organizations[0])
        relations = []
        for course, product in zip(courses, products):
            relations.append(
                factories.CourseProductRelationFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/course-product-relations/"
                f"{relations[0].id}/"
            )

        self.assertEqual(response.status_code, 401)

    def test_api_organizations_course_product_relations_read_details_with_accesses(
        self,
    ):
        """
        Get all CourseProductRelation from an organization
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)
        factories.UserOrganizationAccessFactory(
            organization=organizations[0], user=user
        )
        relations = []
        for course, product in zip(courses, products):
            relations.append(
                factories.CourseProductRelationFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(12):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[0].id}/course-product-relations/"
                    f"{relations[0].id}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(str(relations[0].id), content["id"])

    def test_api_organizations_course_product_relations_read_details_without_access(
        self,
    ):
        """
        Cannot get a single CourseProductRelation from an organization without access
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)

        relations = []
        for course, product in zip(courses, products):
            relations.append(
                factories.CourseProductRelationFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )

        with self.assertNumQueries(1):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[0].id}/course-product-relations/"
                    f"{relations[0].id}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, 404)

    def test_api_organizations_course_product_relations_create_authenticated(self):
        """
        Authenticated users should not be able to
        create a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course": str(course.id),
                "product": str(product.id),
            },
        )

        self.assertContains(response, 'Method \\"POST\\" not allowed.', status_code=405)
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_organizations_course_product_relations_create_anonymous(self):
        """
        Anonymous users should not be able to
        create a course product relation.
        """
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/",
            data={
                "course": str(course.id),
                "product": str(product.id),
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_organizations_course_product_relations_update_authenticated(self):
        """
        Authenticated users should not be able to
        update a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        relation = factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course": "notacourseid",
                "product": str(product.id),
            },
        )

        self.assertEqual(response.status_code, 405)
        relation.refresh_from_db()
        self.assertEqual(relation.course.id, course.id)

    def test_api_organizations_course_product_relations_update_anonymous(self):
        """
        Anonymous users should not be able to
        update a course product relation.
        """

        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        relation = factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/{relation.id}/",
            data={
                "course": "notacourseid",
                "product": str(product.id),
            },
        )

        self.assertEqual(response.status_code, 401)
        relation.refresh_from_db()
        self.assertEqual(relation.course.id, course.id)

    def test_api_organizations_course_product_relations_patch_authenticated(self):
        """
        Authenticated users should not be able to
        patch a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        relation = factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course": "notacourseid",
            },
        )

        self.assertEqual(response.status_code, 405)
        relation.refresh_from_db()
        self.assertEqual(relation.course.id, course.id)

    def test_api_organizations_course_product_relations_patch_anonymous(self):
        """
        Anonymous users should not be able to
        update a course product relation.
        """

        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        relation = factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/{relation.id}/",
            data={
                "course": "notacourseid",
            },
        )

        self.assertEqual(response.status_code, 401)
        relation.refresh_from_db()
        self.assertEqual(relation.course.id, course.id)

    def test_api_organizations_course_product_relations_delete_authenticated(self):
        """
        Authenticated users should not be able to
        delete a course product relation.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        relation = factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/{relation.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            models.CourseProductRelation.objects.filter(id=relation.id).exists()
        )

    def test_api_organizations_course_product_relations_delete_anonymous(self):
        """
        Anonymous users should not be able to
        delete a course product relation.
        """

        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        relation = factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/course-product-relations/{relation.id}/",
        )

        self.assertEqual(response.status_code, 401)
        self.assertTrue(
            models.CourseProductRelation.objects.filter(id=relation.id).exists()
        )
