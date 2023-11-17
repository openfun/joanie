"""
Test suite for Course Admin API.
"""
import random

from django.test import TestCase

from joanie.core import factories


class CourseAdminApiTest(TestCase):
    """
    Test suite for Course Admin API.
    """

    maxDiff = None

    def test_admin_api_course_request_without_authentication(self):
        """
        Anonymous users should not be able to request courses endpoint.
        """
        response = self.client.get("/api/v1.0/admin/courses/")

        self.assertEqual(response.status_code, 401)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_course_request_with_lambda_user(self):
        """
        Lambda user should not be able to request courses endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/courses/")

        self.assertEqual(response.status_code, 403)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_admin_api_course_list(self):
        """
        Staff user should be able to get a paginated list of courses.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        courses_count = random.randint(1, 10)
        courses = factories.CourseFactory.create_batch(courses_count)

        response = self.client.get("/api/v1.0/admin/courses/")

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.json(),
            {
                "count": courses_count,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(course.id),
                        "code": course.code,
                        "title": course.title,
                    }
                    for course in courses
                ],
            },
        )

    def test_admin_api_course_list_filter_by_query(self):
        """
        Staff user should be able to get a paginated list of courses filtered through a search text
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        courses_count = random.randint(1, 10)
        [course, *_] = factories.CourseFactory.create_batch(courses_count)

        response = self.client.get("/api/v1.0/admin/courses/?query=")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], courses_count)

        response = self.client.get(f"/api/v1.0/admin/courses/?query={course.title}")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(course.id))

        response = self.client.get(f"/api/v1.0/admin/courses/?query={course.code}")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(course.id))

    def test_admin_api_course_list_filter_by_query_language(self):
        """
        Staff user should be able to get a paginated list of courses filtered through a search text
        and with different languages
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        item = factories.CourseFactory(title="Lesson 1")
        item.translations.create(language_code="fr-fr", title="Leçon 1")

        response = self.client.get("/api/v1.0/admin/courses/?query=lesson")
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Lesson 1")

        response = self.client.get(
            "/api/v1.0/admin/courses/?query=Leçon", HTTP_ACCEPT_LANGUAGE="fr-fr"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Leçon 1")

        response = self.client.get(
            "/api/v1.0/admin/courses/?query=Lesson", HTTP_ACCEPT_LANGUAGE="fr-fr"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Leçon 1")

    def test_admin_api_course_get(self):
        """
        Staff user should be able to get a course through its id
        with detailed information.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        course_runs = factories.CourseRunFactory.create_batch(
            2, course=course, languages=["fr"]
        )

        # Add course access to the course
        accesses_count = random.randint(0, 5)
        factories.UserCourseAccessFactory.create_batch(accesses_count, course=course)

        response = self.client.get(f"/api/v1.0/admin/courses/{course.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(course.id),
                "code": course.code,
                "course_runs": [
                    {
                        "id": str(course_run.id),
                        "start": course_run.start.isoformat().replace("+00:00", "Z"),
                        "end": course_run.end.isoformat().replace("+00:00", "Z"),
                        "enrollment_start": course_run.enrollment_start.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "enrollment_end": course_run.enrollment_end.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "languages": course_run.languages,
                        "title": course_run.title,
                        "is_gradable": course_run.is_gradable,
                        "is_listed": course_run.is_listed,
                        "resource_link": course_run.resource_link,
                    }
                    for course_run in reversed(course_runs)
                ],
                "cover": {
                    "size": course.cover.size,
                    "src": f"http://testserver{course.cover.url}.1x1_q85.webp",
                    "srcset": (
                        f"http://testserver{course.cover.url}.1920x1080_q85_crop-smart_upscale.webp "  # pylint: disable=line-too-long
                        "1920w, "
                        f"http://testserver{course.cover.url}.1280x720_q85_crop-smart_upscale.webp "  # pylint: disable=line-too-long
                        "1280w, "
                        f"http://testserver{course.cover.url}.768x432_q85_crop-smart_upscale.webp "  # pylint: disable=line-too-long
                        "768w, "
                        f"http://testserver{course.cover.url}.384x216_q85_crop-smart_upscale.webp "  # pylint: disable=line-too-long
                        "384w"
                    ),
                    "height": course.cover.height,
                    "width": course.cover.width,
                    "filename": course.cover.name,
                },
                "title": course.title,
                "organizations": [],
                "product_relations": [],
                "state": {
                    "priority": course.state["priority"],
                    "datetime": course.state["datetime"]
                    .isoformat()
                    .replace("+00:00", "Z")
                    if course.state["datetime"]
                    else None,
                    "call_to_action": course.state["call_to_action"],
                    "text": course.state["text"],
                },
                "accesses": [
                    {
                        "id": str(access.id),
                        "role": access.role,
                        "user": {
                            "id": str(access.user.id),
                            "full_name": access.user.get_full_name(),
                            "username": access.user.username,
                        },
                    }
                    for access in course.accesses.all()
                ],
            },
        )

    def test_admin_api_course_create(self):
        """
        Staff user should be able to create a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        product = factories.ProductFactory()
        data = {
            "code": "COURSE-001",
            "title": "Course 001",
            "organization_ids": [str(organization.id)],
            "product_relations": [
                {
                    "product_id": str(product.id),
                    "organization_ids": [str(organization.id)],
                }
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/courses/", content_type="application/json", data=data
        )

        self.assertEqual(response.status_code, 201)
        content = response.json()

        self.assertIsNotNone(content["code"])
        self.assertEqual(content["code"], "COURSE-001")
        self.assertListEqual(
            content["organizations"],
            [
                {
                    "code": organization.code,
                    "title": organization.title,
                    "id": str(organization.id),
                }
            ],
        )
        self.assertEqual(len(content["product_relations"]), 1)

    def test_admin_api_course_update(self):
        """
        Staff user should be able to update a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory(code="COURSE-001")
        organization = factories.OrganizationFactory()
        payload = {
            "code": "UPDATED-COURSE-001",
            "title": "Updated Course 001",
            "organization_ids": [str(organization.id)],
        }

        response = self.client.put(
            f"/api/v1.0/admin/courses/{course.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))
        self.assertEqual(content["code"], "UPDATED-COURSE-001")
        self.assertEqual(content["title"], "Updated Course 001")
        self.assertListEqual(
            content["organizations"],
            [
                {
                    "code": organization.code,
                    "title": organization.title,
                    "id": str(organization.id),
                }
            ],
        )

    def test_admin_api_course_partially_update(self):
        """
        Staff user should be able to partially update a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory(code="COURSE-001", title="Course 001")
        organization = factories.OrganizationFactory(code="ORG-002")
        product = factories.ProductFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/courses/{course.id}/",
            content_type="application/json",
            data={
                "title": "Updated Course 001",
                "organization_ids": [str(organization.id)],
                "product_relations": [
                    {
                        "product_id": str(product.id),
                        "organization_ids": [str(organization.id)],
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))
        self.assertEqual(content["title"], "Updated Course 001")
        self.assertEqual(content["organizations"][0]["code"], "ORG-002")
        self.assertEqual(len(content["product_relations"]), 1)

    def test_admin_api_course_delete(self):
        """
        Staff user should be able to delete a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()

        response = self.client.delete(f"/api/v1.0/admin/courses/{course.id}/")

        self.assertEqual(response.status_code, 204)
