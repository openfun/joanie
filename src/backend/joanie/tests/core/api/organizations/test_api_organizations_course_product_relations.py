"""
Test suite for Organization's CourseProductRelation API endpoint.
"""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationCourseProductRelationApiTest(BaseAPITestCase):
    """
    Test suite for Organization's CourseProductRelation API endpoint.
    """

    def test_api_organizations_offerings_read_list_anonymous(self):
        """
        Anonymous user cannot query all CourseProductRelation form an organization
        """

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)
        factories.UserOrganizationAccessFactory(organization=organizations[0])
        offerings = []
        for course, product in zip(courses, products, strict=True):
            offerings.append(
                factories.OfferingFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/offerings/",
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_offerings_read_list_with_accesses(self):
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
        offerings = []
        for course, product in zip(courses, products, strict=True):
            offerings.append(
                factories.OfferingFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(156):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/offerings/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on the product serializer
        with self.assertNumQueries(4):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/offerings/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 5)
        self.assertEqual(
            {str(x["id"]) for x in content["results"]},
            {str(x.id) for x in offerings},
        )

    def test_api_organizations_offerings_read_list_without_access(self):
        """
        Cannot get all CourseProductRelation from an organization without access
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)

        offerings = []
        for course, product in zip(courses, products, strict=True):
            offerings.append(
                factories.OfferingFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/offerings/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_organizations_offerings_read_details_anonymous(self):
        """
        Anonymous user cannot query a single CourseProductRelation form an organization
        """

        organizations = factories.OrganizationFactory.create_batch(2)
        courses = factories.CourseFactory.create_batch(5)
        products = factories.ProductFactory.create_batch(5)
        factories.UserOrganizationAccessFactory(organization=organizations[0])
        offerings = []
        for course, product in zip(courses, products, strict=True):
            offerings.append(
                factories.OfferingFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/offerings/{offerings[0].id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_offerings_read_details_with_accesses(
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
        offerings = []
        for course, product in zip(courses, products, strict=True):
            offerings.append(
                factories.OfferingFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )
        with self.assertNumQueries(51):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[0].id}/offerings/"
                    f"{offerings[0].id}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        # A second call to the url should benefit from caching on the product serializer
        with self.assertNumQueries(3):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[0].id}/offerings/"
                    f"{offerings[0].id}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(str(offerings[0].id), content["id"])

    def test_api_organizations_offerings_read_details_without_access(
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

        offerings = []
        for course, product in zip(courses, products, strict=True):
            offerings.append(
                factories.OfferingFactory(
                    course=course, product=product, organizations=[organizations[0]]
                )
            )

        with self.assertNumQueries(1):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{organizations[0].id}/offerings/"
                    f"{offerings[0].id}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_organizations_offerings_create_authenticated(self):
        """
        Authenticated users should not be able to
        create an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/offerings/",
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

    def test_api_organizations_offerings_create_anonymous(self):
        """
        Anonymous users should not be able to
        create an offering.
        """
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/offerings/",
            data={
                "course_id": str(course.id),
                "product_id": str(product.id),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(models.CourseProductRelation.objects.count(), 0)

    def test_api_organizations_offerings_update_authenticated(self):
        """
        Authenticated users should not be able to
        update an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": "notacourseid",
                "product_id": str(product.id),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        offering.refresh_from_db()
        self.assertEqual(offering.course.id, course.id)

    def test_api_organizations_offerings_update_anonymous(self):
        """
        Anonymous users should not be able to
        update an offering.
        """

        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/offerings/{offering.id}/",
            data={
                "course_id": "notacourseid",
                "product_id": str(product.id),
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        offering.refresh_from_db()
        self.assertEqual(offering.course.id, course.id)

    def test_api_organizations_offerings_patch_authenticated(self):
        """
        Authenticated users should not be able to
        patch an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "course_id": "notacourseid",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        offering.refresh_from_db()
        self.assertEqual(offering.course.id, course.id)

    def test_api_organizations_offerings_patch_anonymous(self):
        """
        Anonymous users should not be able to
        update an offering.
        """

        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/offerings/{offering.id}/",
            data={
                "course_id": "notacourseid",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        offering.refresh_from_db()
        self.assertEqual(offering.course.id, course.id)

    def test_api_organizations_offerings_delete_authenticated(self):
        """
        Authenticated users should not be able to
        delete an offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/offerings/{offering.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertTrue(
            models.CourseProductRelation.objects.filter(id=offering.id).exists()
        )

    def test_api_organizations_offerings_delete_anonymous(self):
        """
        Anonymous users should not be able to
        delete an offering.
        """

        organization = factories.OrganizationFactory.create()
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[])
        offering = factories.OfferingFactory(
            course=course, product=product, organizations=[organization]
        )

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/offerings/{offering.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertTrue(
            models.CourseProductRelation.objects.filter(id=offering.id).exists()
        )

    # pylint: disable=too-many-locals
    def test_api_organizations_offerings_filter_by_query_product_title(
        self,
    ):
        """
        An authenticated user should be able to filter offering by
        product title if he has access to the organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization_1 = factories.OrganizationFactory()
        organization_2 = factories.OrganizationFactory()
        organization_3 = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization_1, user=user)
        factories.UserOrganizationAccessFactory(organization=organization_2, user=user)
        product_1 = factories.ProductFactory(
            title="Introduction to resource filtering", courses=[]
        )
        product_2 = factories.ProductFactory(
            title="Advanced aerodynamic flows", courses=[]
        )
        product_3 = factories.ProductFactory(
            title="Rubber management on a single-seater", courses=[]
        )
        product_4 = factories.ProductFactory(
            title="Single-seater porpoising introduction", courses=[]
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
        product_4.translations.create(
            language_code="fr-fr", title="Introduction au marsouinage d'une monoplace"
        )
        relations_organization_1 = []
        for product in [product_1, product_3]:
            relations_organization_1.append(
                factories.OfferingFactory(
                    organizations=[organization_1], product=product
                )
            )
        offering_1 = factories.OfferingFactory(
            product=product_2,
            organizations=[organization_1],
        )
        relations_organization_1.append(offering_1)

        offering_2 = factories.OfferingFactory(
            product=product_4, organizations=[organization_2]
        )
        factories.OfferingFactory(organizations=[organization_3])

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
                f"/api/v1.0/organizations/{organization_1.id}/offerings/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0].get("id"), str(offering_1.id))

        # When parsing a product title that the organization is not linked to, it should
        # return no result
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/"
            f"offerings/?query={offering_2.product.title}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # When parsing nothing we should find the 1 offering that is linked to the
        # organization 2
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_2.id}/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(offering_2.id))

        # When parsing nothing we should find the 3 offerings linked to the
        # organization 1
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {str(x["id"]) for x in content["results"]},
            {str(x.id) for x in relations_organization_1},
        )

        # Should get 0 result in return with a title that does not exist
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/offerings/?query=fake",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # Should get 0 result in return because we don't have organization access
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_3.id}/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    # pylint: disable=too-many-locals
    def test_api_organizations_offerings_filter_by_query_course_code(
        self,
    ):
        """
        An authenticated user should be able to filter offering by
        course code if he has access to the organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization_1 = factories.OrganizationFactory()
        organization_2 = factories.OrganizationFactory()
        organization_3 = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization_1, user=user)
        factories.UserOrganizationAccessFactory(organization=organization_2, user=user)
        course_1 = factories.CourseFactory(code="MYCODE_0095")
        course_2 = factories.CourseFactory(code="MYCODE_0096")
        course_3 = factories.CourseFactory(code="MYCODE_0097")
        course_4 = factories.CourseFactory(code="MYCODE_0098")
        # Create 3 CourseProductRelations for organization 1
        relations_organization_1 = []
        for course in [course_1, course_3]:
            relations_organization_1.append(
                factories.OfferingFactory(organizations=[organization_1], course=course)
            )
        offering_1 = factories.OfferingFactory(
            course=course_2,
            organizations=[organization_1],
        )
        relations_organization_1.append(offering_1)

        # 1 CourseProductRelation for organization 2
        offering_2 = factories.OfferingFactory(
            course=course_4, organizations=[organization_2]
        )
        # 1 CourseProductRelation for organization 3
        factories.OfferingFactory(organizations=[organization_3])
        # We should retrieve only one course out of 3 from the course code
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/"
            f"offerings/?query={offering_1.course.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(offering_1.id))

        # When parsing a course code that the organization is not linked to, it should
        # return no result
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/"
            f"offerings/?query={offering_2.course.code}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # When parsing MYCODE_009 with organization 2, we should find 1 CourseProductRelation
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_2.id}/offerings/"
            f"?query={offering_2.course.code[:1]}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0].get("id"), str(offering_2.id))

        # When parsing nothing we should find the 3 offerings linked to the
        # organization 1
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {str(x["id"]) for x in content["results"]},
            {str(x.id) for x in relations_organization_1},
        )

        # Should get 0 result in return with a title that does not exist
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/offerings/?query=fake",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # Should get 0 result in return because we don't have organization access
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_3.id}/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_organizations_offerings_filter_by_query_organization_title(
        self,
    ):
        """
        An authenticated user should be able to filter offering by
        organization title if he has access to the organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization_1 = factories.OrganizationFactory(
            title="Digital University of Innovation"
        )
        organization_2 = factories.OrganizationFactory(
            title="Online Digital University"
        )
        organization_3 = factories.OrganizationFactory(
            title="University of Digital Learning"
        )
        organization_1.translations.create(
            language_code="fr-fr", title="Université Numérique d'Innovation"
        )
        organization_2.translations.create(
            language_code="fr-fr", title="Université digital en ligne"
        )
        organization_3.translations.create(
            language_code="fr-fr", title="Université de l'Apprentissage Numérique"
        )
        factories.UserOrganizationAccessFactory(organization=organization_1, user=user)
        factories.UserOrganizationAccessFactory(organization=organization_2, user=user)
        # Create 3 CourseProductRelations for organization 1
        cpr1 = factories.OfferingFactory(
            organizations=[organization_1, organization_2],
            # course=courses[0]
        )
        cpr2 = factories.OfferingFactory(
            organizations=[organization_1, organization_2],
            # course=courses[1]
        )
        cpr3 = factories.OfferingFactory(organizations=[organization_1])
        # 1 CourseProductRelation for organization 3
        factories.OfferingFactory(organizations=[organization_3])

        # We should retrieve 3 CourseProductRelation from organization 1
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/"
            f"offerings/?query={organization_1.title}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(cpr1.id), str(cpr2.id), str(cpr3.id)],
        )

        # We should retrieve 2 CourseProductRelation from organization 2
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_2.id}/"
            f"offerings/?query={organization_2.title}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(cpr1.id), str(cpr2.id)],
        )

        # We should retrieve 0 CourseProductRelation from organization 3 because no access
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_3.id}/"
            f"offerings/?query={organization_3.title}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # Prepare queries to test
        queries = [
            "Online Digital University",
            "Université digital en ligne",
            "Digital",
            "Dig",
            "Di",
            "Uni",
            "tal",
            "ta",
            "en",
            "git",
            "D",
            "o",
        ]

        for query in queries:
            # We should find 2 CourseProductRelation
            response = self.client.get(
                f"/api/v1.0/organizations/{organization_2.id}/offerings/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 2)
            self.assertCountEqual(
                [result["id"] for result in content["results"]],
                [str(cpr1.id), str(cpr2.id)],
            )

        # We should retrieve 3 CourseProductRelation
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/offerings/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(cpr1.id), str(cpr2.id), str(cpr3.id)],
        )

        # We should retrieve 0 CourseProductRelation
        response = self.client.get(
            f"/api/v1.0/organizations/{organization_1.id}/"
            f"offerings/?query=fakeOrganizationTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)
