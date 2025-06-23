"""
Test suite for Course Admin API.
"""

import datetime
import random
import uuid
from http import HTTPStatus

from django.test import TestCase

from timedelta_isoformat import timedelta as timedelta_isoformat

from joanie.core import factories
from joanie.core.models.courses import Course
from joanie.tests import format_date


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

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
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

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], courses_count)

        response = self.client.get(f"/api/v1.0/admin/courses/?query={course.title}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(course.id))

        response = self.client.get(f"/api/v1.0/admin/courses/?query={course.code}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Lesson 1")

        response = self.client.get(
            "/api/v1.0/admin/courses/?query=Leçon", HTTP_ACCEPT_LANGUAGE="fr-fr"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Leçon 1")

        response = self.client.get(
            "/api/v1.0/admin/courses/?query=Lesson", HTTP_ACCEPT_LANGUAGE="fr-fr"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["title"], "Leçon 1")

    def test_admin_api_course_list_filter_by_organization_ids(self):
        """
        Staff user should be able to get a paginated list of courses filtered through
        one or several organization id
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organizations = factories.OrganizationFactory.create_batch(2)

        for organization in organizations:
            factories.CourseFactory.create(organizations=[organization])

        # - Create random courses
        factories.CourseFactory.create_batch(2)

        for organization in organizations:
            response = self.client.get(
                f"/api/v1.0/admin/courses/?organization_ids={organization.id}"
            )
            course = organization.courses.first()
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(course.id))

        # - Test with several organizations
        response = self.client.get(
            f"/api/v1.0/admin/courses/"
            f"?organization_ids={organizations[0].id}"
            f"&organization_ids={organizations[1].id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        # Test with an organization that does not have any course
        other_organization = factories.OrganizationFactory()
        response = self.client.get(
            f"/api/v1.0/admin/courses/?organization_ids={other_organization.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # Test with non existing organization
        unknown_id = uuid.uuid4()
        response = self.client.get(
            f"/api/v1.0/admin/courses/?organization_ids={unknown_id}"
        )
        self.assertContains(
            response,
            '{"organization_ids":['
            f'"Select a valid choice. {unknown_id} is not one of the available choices."'
            "]}",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_admin_api_course_list_filter_by_invalid_organization_ids(self):
        """
        Staff user should be able to get a paginated list of courses filtered
        through an organization id and get a bad request if the organization id is not
        a valid uuid.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/courses/?organization_ids=invalid")

        self.assertContains(
            response,
            '{"organization_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_admin_api_course_filter_query_by_course_id(self):
        """
        Authenticated users should be able to filter courses by their id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        courses = factories.CourseFactory.create_batch(3)

        response = self.client.get(
            "/api/v1.0/admin/courses/",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        response = self.client.get(
            f"/api/v1.0/admin/courses/?ids={courses[0].id}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(courses[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/courses/?ids={courses[0].id}&ids={courses[1].id}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(courses[0].id))
        self.assertEqual(content["results"][1]["id"], str(courses[1].id))

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
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(course.id),
                "code": course.code,
                "course_runs": [
                    {
                        "id": str(course_run.id),
                        "start": format_date(course_run.start),
                        "end": format_date(course_run.end),
                        "enrollment_start": format_date(course_run.enrollment_start),
                        "enrollment_end": format_date(course_run.enrollment_end),
                        "languages": course_run.languages,
                        "title": course_run.title,
                        "is_gradable": course_run.is_gradable,
                        "is_listed": course_run.is_listed,
                        "resource_link": course_run.resource_link,
                        "state": {
                            "call_to_action": course_run.state.get("call_to_action"),
                            "datetime": format_date(course_run.state.get("datetime")),
                            "priority": course_run.state.get("priority"),
                            "text": course_run.state.get("text"),
                        },
                        "uri": course_run.uri,
                    }
                    for course_run in reversed(course_runs)
                ],
                "cover": {
                    "size": course.cover.size,
                    "src": f"http://testserver{course.cover.url}.1x1_q85.webp",
                    "srcset": (
                        f"http://testserver{course.cover.url}.1920x1080_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "1920w, "
                        f"http://testserver{course.cover.url}.1280x720_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "1280w, "
                        f"http://testserver{course.cover.url}.768x432_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "768w, "
                        f"http://testserver{course.cover.url}.384x216_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                        "384w"
                    ),
                    "height": course.cover.height,
                    "width": course.cover.width,
                    "filename": course.cover.name,
                },
                "effort": timedelta_isoformat(
                    seconds=course.effort.total_seconds()
                ).isoformat(),
                "title": course.title,
                "organizations": [],
                "offerings": [],
                "state": {
                    "priority": course.state["priority"],
                    "datetime": format_date(course.state["datetime"]),
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
                            "email": access.user.email,
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
        product = factories.ProductFactory(courses=[])
        data = {
            "code": "00001",
            "title": "Course 001",
            "organization_ids": [str(organization.id)],
            "offerings": [
                {
                    "product_id": str(product.id),
                    "organization_ids": [str(organization.id)],
                }
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/courses/", content_type="application/json", data=data
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()

        self.assertIsNotNone(content["code"])
        self.assertEqual(content["code"], "00001")
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
        self.assertEqual(len(content["offerings"]), 1)

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
            "effort": "PT10H",
        }

        response = self.client.put(
            f"/api/v1.0/admin/courses/{course.id}/",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))
        self.assertEqual(content["code"], "UPDATED-COURSE-001")
        self.assertEqual(content["title"], "Updated Course 001")
        self.assertEqual(content["effort"], "PT10H")
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

        courses_count = Course.objects.all().count()
        course = Course.objects.all().first()

        self.assertEqual(courses_count, 1)
        self.assertEqual(course.effort, datetime.timedelta(seconds=36000))

    def test_admin_api_course_partially_update(self):
        """
        Staff user should be able to partially update a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory(code="00001", title="Course 00001")
        organization = factories.OrganizationFactory(code="ORG-002")
        product = factories.ProductFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/courses/{course.id}/",
            content_type="application/json",
            data={
                "title": "Updated Course 00001",
                "organization_ids": [str(organization.id)],
                "offerings": [
                    {
                        "product_id": str(product.id),
                        "organization_ids": [str(organization.id)],
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["id"], str(course.id))
        self.assertEqual(content["title"], "Updated Course 00001")
        self.assertEqual(content["organizations"][0]["code"], "ORG-002")
        self.assertEqual(len(content["offerings"]), 1)

    def test_admin_api_course_delete(self):
        """
        Staff user should be able to delete a course.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()

        response = self.client.delete(f"/api/v1.0/admin/courses/{course.id}/")

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_admin_api_course_create_effort_with_iso_8601_formatted_value(self):
        """
        Staff user should be able to create a course and give an effort value formatted in ISO
        8601. We make sure that the object is created, and we verify that the value saved in
        database is of type python's `datetime.timedelta`.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        product = factories.ProductFactory(courses=[])
        data = {
            "effort": "PT10H",  # represents 10 hours in ISO 8601
            "code": "00001",
            "title": "Course 001",
            "organization_ids": [str(organization.id)],
            "offerings": [
                {
                    "product_id": str(product.id),
                    "organization_ids": [str(organization.id)],
                }
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/courses/", content_type="application/json", data=data
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        courses_count = Course.objects.all().count()
        course = Course.objects.all().first()

        self.assertEqual(courses_count, 1)
        self.assertNotEqual(course.effort, "PT10H")
        self.assertEqual(course.effort, datetime.timedelta(seconds=36000))

    def test_admin_api_course_create_effort_with_timedelta_value(self):
        """
        Staff user should be able to create a course and give python's `datetime.timedelta`
        value for the effort.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        organization = factories.OrganizationFactory()
        product = factories.ProductFactory(courses=[])
        data = {
            "effort": datetime.timedelta(
                seconds=36000
            ),  # represents 10 hours in ISO 8601
            "code": "00001",
            "title": "Course 001",
            "organization_ids": [str(organization.id)],
            "offerings": [
                {
                    "product_id": str(product.id),
                    "organization_ids": [str(organization.id)],
                }
            ],
        }

        response = self.client.post(
            "/api/v1.0/admin/courses/", content_type="application/json", data=data
        )

        course = Course.objects.all().first()

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(course.effort, datetime.timedelta(seconds=36000))
