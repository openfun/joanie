"""
Test suite for Product Admin API.
"""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories, models


class ProductAdminApiTargetCoursesTest(TestCase):
    """
    Test suite for nested target courses Product Admin API endpoints.
    """

    maxDiff = None

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
        offers = models.ProductTargetCourseRelation.objects.filter(product=product)
        self.assertEqual(offers.get(course=courses[1]).position, 0)
        self.assertEqual(offers.get(course=courses[3]).position, 1)
        self.assertEqual(offers.get(course=courses[0]).position, 2)
        self.assertEqual(offers.get(course=courses[2]).position, 3)
        self.assertEqual(offers.get(course=courses[4]).position, 4)
