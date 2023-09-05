"""
Test suite for Product Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories, models


class ProductAdminApiTest(TestCase):
    """
    Test suite for Product Admin API.
    """

    def test_admin_api_product_request_without_authentication(self):
        """
        Anonymous users should not be able to request products endpoint.
        """
        response = self.client.get("/api/v1.0/admin/products/")

        self.assertEqual(response.status_code, 401)
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

        self.assertEqual(response.status_code, 403)
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

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], product_count)

    def test_admin_api_product_get(self):
        """
        Staff user should be able to get a product through its id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[target_course])
        relation = models.CourseProductRelation.objects.get(product=product)
        target_course_relation = models.ProductTargetCourseRelation.objects.get(
            product=product.id, course=target_course.id
        )
        response = self.client.get(f"/api/v1.0/admin/products/{product.id}/")

        self.assertEqual(response.status_code, 200)
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
            "certificate_definition": product.certificate_definition,
            "target_courses": [
                {
                    "id": str(target_course_relation.id),
                    "course": {
                        "code": target_course_relation.course.code,
                        "title": target_course_relation.course.title,
                        "id": str(target_course_relation.course.id),
                        "state": {
                            "priority": target_course_relation.course.state["priority"],
                            "datetime": target_course_relation.course.state["datetime"],
                            "call_to_action": target_course_relation.course.state[
                                "call_to_action"
                            ],
                            "text": target_course_relation.course.state["text"],
                        },
                    },
                    "course_runs": [],
                }
            ],
            "course_relations": [
                {
                    "id": str(relation.id),
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
                                f"{relation.course.cover.url}.1920x1080_q85_crop-smart_upscale.webp 1920w, "  # noqa pylint: disable=line-too-long
                                f"{relation.course.cover.url}.1280x720_q85_crop-smart_upscale.webp 1280w, "  # noqa pylint: disable=line-too-long
                                f"{relation.course.cover.url}.768x432_q85_crop-smart_upscale.webp 768w, "  # noqa pylint: disable=line-too-long
                                f"{relation.course.cover.url}.384x216_q85_crop-smart_upscale.webp 384w"  # noqa pylint: disable=line-too-long
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
        }

        response = self.client.post("/api/v1.0/admin/products/", data=data)

        self.assertEqual(response.status_code, 201)
        content = response.json()
        self.assertIsNotNone(content["id"])
        self.assertEqual(content["title"], "Product 001")

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
            "type": "enrollment",
            "call_to_action": "Purchase now",
            "description": "This is a product description",
        }

        response = self.client.put(
            f"/api/v1.0/admin/products/{product.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(product.id))
        self.assertEqual(content["price"], 100)

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

        self.assertEqual(response.status_code, 200)
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

        self.assertEqual(response.status_code, 204)

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
        self.assertEqual(response.status_code, 401)
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
        self.assertEqual(response.status_code, 201)
        relation = models.ProductTargetCourseRelation.objects.get()
        self.assertEqual(
            response.json(),
            {
                "id": str(relation.id),
                "course": str(course.id),
                "product": str(product.id),
                "course_runs": [],
            },
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
        self.assertEqual(response.status_code, 401)
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
        relation = models.ProductTargetCourseRelation.objects.get(
            product=product, course=course
        )
        response = self.client.delete(
            f"/api/v1.0/admin/products/{product.id}/target-courses/{relation.id}/",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(models.ProductTargetCourseRelation.objects.count(), 0)
        product.refresh_from_db()
        self.assertEqual(product.target_courses.count(), 0)
