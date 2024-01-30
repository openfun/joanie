"""
Test suite for Product Admin API.
"""
import random
from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories, models


class ProductAdminApiTest(TestCase):
    """
    Test suite for Product Admin API.
    """

    def test_admin_api_product_request_without_authentication(self):
        """
        Anonymous users should not be able to request products endpoint.
        """
        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_product_request_with_lambda_user(self):
        """
        Lambda user should not be able to request products endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_product_list(self):
        """
        Staff user should be able to get paginated list of products
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product_count = random.randint(1, 10)
        factories.ProductFactory.create_batch(product_count)

        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], product_count)

    def test_admin_api_product_list_filter_by_type(self):
        """
        Staff user should be able to get paginated list of products filtered by
        type
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            factories.ProductFactory.create(type=product_type)

        for [product_type, _] in enums.PRODUCT_TYPE_CHOICES:
            response = self.client.get(f"/api/v1.0/admin/products/?type={product_type}")

            product = models.Product.objects.get(type=product_type)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(product.id))

    def test_admin_api_product_list_filter_by_invalid_type(self):
        """
        Staff user should be able to get paginated list of products filtered by
        type but an error should be returned if the type is not valid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/products/?type=invalid_type")

        self.assertContains(
            response,
            '{"type":["'
            "Select a valid choice. invalid_type is not one of the available choices."
            '"]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_admin_api_product_get(self):
        """
        Staff user should be able to get a product through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        contract_definition = factories.ContractDefinitionFactory()
        product = factories.ProductFactory(contract_definition=contract_definition)
        relation = models.CourseProductRelation.objects.get(product=product)
        courses = factories.CourseFactory.create_batch(3)
        relations = []
        relations.append(
            models.ProductTargetCourseRelation(
                course=courses[0], product=product, position=2
            )
        )
        relations[0].save()
        relations.append(
            models.ProductTargetCourseRelation(
                course=courses[1], product=product, position=0
            )
        )
        relations[1].save()
        relations.append(
            models.ProductTargetCourseRelation(
                course=courses[2], product=product, position=1
            )
        )
        relations[2].save()

        response = self.client.get(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        expected_result = {
            "id": str(product.id),
            "title": product.title,
            "description": product.description,
            "call_to_action": product.call_to_action,
            "type": product.type,
            "price": float(product.price),
            "price_currency": "EUR",
            "certificate_definition": {
                "description": "",
                "id": str(product.certificate_definition.id),
                "name": product.certificate_definition.name,
                "template": product.certificate_definition.template,
                "title": product.certificate_definition.title,
            },
            "contract_definition": {
                "id": str(contract_definition.id),
                "title": contract_definition.title,
                "description": contract_definition.description,
                "name": contract_definition.name,
                "language": contract_definition.language,
                "body": contract_definition.body,
            },
            "target_courses": [
                {
                    "id": str(relations[1].id),
                    "course": {
                        "id": str(courses[1].id),
                        "code": courses[1].code,
                        "title": courses[1].title,
                        "state": {
                            "priority": courses[1].state["priority"],
                            "datetime": courses[1].state["datetime"],
                            "call_to_action": courses[1].state["call_to_action"],
                            "text": courses[1].state["text"],
                        },
                    },
                    "course_runs": [],
                    "is_graded": relations[1].is_graded,
                    "position": relations[1].position,
                },
                {
                    "id": str(relations[2].id),
                    "course": {
                        "id": str(courses[2].id),
                        "code": courses[2].code,
                        "title": courses[2].title,
                        "state": {
                            "priority": courses[2].state["priority"],
                            "datetime": courses[2].state["datetime"],
                            "call_to_action": courses[2].state["call_to_action"],
                            "text": courses[2].state["text"],
                        },
                    },
                    "course_runs": [],
                    "is_graded": relations[2].is_graded,
                    "position": relations[2].position,
                },
                {
                    "id": str(relations[0].id),
                    "course": {
                        "id": str(courses[0].id),
                        "code": courses[0].code,
                        "title": courses[0].title,
                        "state": {
                            "priority": courses[0].state["priority"],
                            "datetime": courses[0].state["datetime"],
                            "call_to_action": courses[0].state["call_to_action"],
                            "text": courses[0].state["text"],
                        },
                    },
                    "course_runs": [],
                    "is_graded": relations[0].is_graded,
                    "position": relations[0].position,
                },
            ],
            "instructions": "",
            "course_relations": [
                {
                    "id": str(relation.id),
                    "uri": relation.uri,
                    "can_edit": relation.can_edit,
                    "course": {
                        "id": str(relation.course.id),
                        "code": relation.course.code,
                        "cover": {
                            "filename": relation.course.cover.name,
                            "height": relation.course.cover.height,
                            "width": relation.course.cover.width,
                            "src": f"{relation.course.cover.url}.1x1_q85.webp",
                            "size": relation.course.cover.size,
                            "srcset": (
                                f"{relation.course.cover.url}.1920x1080_q85_crop-scale_upscale.webp 1920w, "  # pylint: disable=line-too-long
                                f"{relation.course.cover.url}.1280x720_q85_crop-scale_upscale.webp 1280w, "  # pylint: disable=line-too-long
                                f"{relation.course.cover.url}.768x432_q85_crop-scale_upscale.webp 768w, "  # pylint: disable=line-too-long
                                f"{relation.course.cover.url}.384x216_q85_crop-scale_upscale.webp 384w"  # pylint: disable=line-too-long
                            ),
                        },
                        "title": relation.course.title,
                        "organizations": [],
                        "state": {
                            "priority": relation.course.state["priority"],
                            "datetime": relation.course.state["datetime"],
                            "call_to_action": relation.course.state["call_to_action"],
                            "text": relation.course.state["text"],
                        },
                    },
                    "organizations": [
                        {
                            "code": relation.organizations.first().code,
                            "title": relation.organizations.first().title,
                            "id": str(relation.organizations.first().id),
                        }
                    ],
                    "order_groups": [],
                }
            ],
        }
        self.assertEqual(content, expected_result)

    def test_admin_api_product_create(self):
        """
        Staff user should be able to create a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "call_to_action": "Purchase now",
            "description": "This is a product description",
            "instructions": "test instruction",
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertEqual(content["instructions"], "test instruction")

    def test_admin_api_product_create_with_blank_description(self):
        """
        Staff user should be able to create a product with blank description.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "call_to_action": "Purchase now",
            "instructions": "Product instructions",
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertEqual(content["description"], "")

    def test_admin_api_product_create_with_blank_instructions(self):
        """
        Staff user should be able to create a product with blank instructions.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        data = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": "enrollment",
            "description": "This is a product description",
            "call_to_action": "Purchase now",
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")
        self.assertEqual(content["instructions"], "")

    def test_admin_api_product_update(self):
        """
        Staff user should be able to update a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(price=200)
        payload = {
            "title": "Product 001",
            "price": "100.00",
            "price_currency": "EUR",
            "type": random.choice(["credential", "certificate"]),
            "call_to_action": "Purchase now",
            "description": "This is a product description",
            "instructions": "This is a test instruction",
        }

        response = self.client.put(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100)
        self.assertEqual(content["instructions"], "This is a test instruction")

    def test_admin_api_product_partially_update(self):
        """
        Staff user should be able to partially update a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(price=100)

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"price": 100.57, "price_currency": "EUR"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100.57)

    def test_admin_api_product_delete(self):
        """
        Staff user should be able to delete a product.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory()

        response = self.client.delete(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_admin_api_product_add_target_course_without_authentication(self):
        """
        Anonymous users should not be able to add a target_course
        """
        product = factories.ProductFactory()
        course = factories.CourseFactory()

        response = self.client.post(
            f"/api/v1.0/admin/products/{product.id}/target-courses/",
            content_type="application/json",
            data={"course": str(course.id)},
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(models.ProductTargetCourseRelation.objects.exists())

    def test_admin_api_product_add_target_course(self):
        """
        Authenticated users should be able to add a target-course to a product
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        course = factories.CourseFactory()
        response = self.client.post(
            f"/api/v1.0/admin/products/{product.id}/target-courses/",
            content_type="application/json",
            data={"course": str(course.id)},
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        relation = models.ProductTargetCourseRelation.objects.get()
        expected_result = {
            "id": str(relation.id),
            "course": {
                "code": relation.course.code,
                "title": relation.course.title,
                "id": str(relation.course.id),
                "state": {
                    "priority": relation.course.state["priority"],
                    "datetime": relation.course.state["datetime"],
                    "call_to_action": relation.course.state["call_to_action"],
                    "text": relation.course.state["text"],
                },
            },
            "is_graded": relation.is_graded,
            "position": relation.position,
            "course_runs": [],
        }
        self.assertEqual(
            response.json(),
            expected_result,
        )

    def test_admin_api_product_add_target_course_empty_course_run(self):
        """
        Authenticated users should be able to add a target-course without
        course run to a product
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        course = factories.CourseFactory()
        response = self.client.post(
            f"/api/v1.0/admin/products/{product.id}/target-courses/",
            content_type="application/json",
            data={"course": str(course.id), "course_runs": ""},
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        relation = models.ProductTargetCourseRelation.objects.get()
        expected_result = {
            "id": str(relation.id),
            "course": {
                "code": relation.course.code,
                "title": relation.course.title,
                "id": str(relation.course.id),
                "state": {
                    "priority": relation.course.state["priority"],
                    "datetime": relation.course.state["datetime"],
                    "call_to_action": relation.course.state["call_to_action"],
                    "text": relation.course.state["text"],
                },
            },
            "is_graded": relation.is_graded,
            "position": relation.position,
            "course_runs": [],
        }
        self.assertEqual(
            response.json(),
            expected_result,
        )

    def test_admin_api_product_delete_target_course_without_authentication(self):
        """
        Anonymous users should not be able to delete a target_course from a product
        """
        product = factories.ProductFactory()
        course = factories.CourseFactory()
        product.target_courses.add(course)
        response = self.client.delete(
            f"/api/v1.0/admin/products/{product.id}/target-courses/{course.id}/",
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(models.ProductTargetCourseRelation.objects.count(), 1)

    def test_admin_api_product_delete_target_course(self):
        """
        Authenticated user should be able to delete a target_course from a product
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        course = factories.CourseFactory()
        product.target_courses.add(course)
        response = self.client.delete(
            f"/api/v1.0/admin/products/{product.id}/target-courses/{course.id}/",
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(models.ProductTargetCourseRelation.objects.count(), 0)
        product.refresh_from_db()
        self.assertEqual(product.target_courses.count(), 0)

    def test_admin_api_product_edit_target_course(self):
        """
        Authenticated user should be able to modify a target_course
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        course = factories.CourseFactory()
        product.target_courses.add(course)
        relation = models.ProductTargetCourseRelation.objects.get(
            product=product, course=course
        )
        relation.is_graded = False
        relation.save()
        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/target-courses/{course.id}/",
            data={"is_graded": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        relation.refresh_from_db()
        self.assertTrue(relation.is_graded)

    def test_admin_api_product_edit_target_course_empty_course_runs(self):
        """
        User can modify a TargetCourse to remove all course_runs
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        course = factories.CourseFactory()
        product.target_courses.add(course)
        relation = models.ProductTargetCourseRelation.objects.get(
            product=product, course=course
        )
        relation.is_graded = False
        relation.save()
        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/target-courses/{course.id}/",
            data={"is_graded": True, "course_runs": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        relation.refresh_from_db()
        self.assertEqual(relation.course_runs.count(), 0)

    def test_admin_api_product_reorder_target_course(self):
        """
        Authenticated user should be able to change target_courses order
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        product = factories.ProductFactory()
        courses = factories.CourseFactory.create_batch(5)
        for course in courses:
            product.target_courses.add(course)
        response = self.client.post(
            f"/api/v1.0/admin/products/{product.id}/target-courses/reorder/",
            data={
                "target_courses": [
                    str(courses[1].id),
                    str(courses[3].id),
                    str(courses[0].id),
                    str(courses[2].id),
                    str(courses[4].id),
                ]
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        relations = models.ProductTargetCourseRelation.objects.filter(product=product)
        self.assertEqual(relations.get(course=courses[1]).position, 0)
        self.assertEqual(relations.get(course=courses[3]).position, 1)
        self.assertEqual(relations.get(course=courses[0]).position, 2)
        self.assertEqual(relations.get(course=courses[2]).position, 3)
        self.assertEqual(relations.get(course=courses[4]).position, 4)

    def test_admin_api_product_update_empty_instructions(self):
        """
        Staff user should be able to update a product with empty instructions.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(
            price=100, instructions="A not empty instruction"
        )

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"instructions": ""},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["instructions"], "")
        product.refresh_from_db()
        self.assertEqual(product.instructions, "")

    def test_admin_api_product_update_trailing_whitespace(self):
        """
        Trailing whitespaces and newline on instructions should remain
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        product = factories.ProductFactory(price=100)

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"instructions": "Test whitespace   "},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["instructions"], "Test whitespace   ")

        response = self.client.patch(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data={"instructions": "Test newline\n\n"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["instructions"], "Test newline\n\n")
