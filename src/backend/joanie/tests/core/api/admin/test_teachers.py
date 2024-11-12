"""Tests for the Teacher Admin API endpoints."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class TeacherAdminApiTest(BaseAPITestCase):
    """Test for the Admin TeacherViewSet."""

    maxDiff = None

    def test_api_admin_teacher_list_anonymous(self):
        """Anonymous users should not be able to list teachers."""
        response = self.client.get("/api/v1.0/admin/teachers/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_teacher_list_non_admin(self):
        """Non admin users should not be able to list teachers."""
        user = factories.UserFactory()
        self.client.login(username=user.username, password="password")
        response = self.client.get("/api/v1.0/admin/teachers/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_teacher_list_admin(self):
        """Admin users should be able to list teachers."""
        teacher = factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get("/api/v1.0/admin/teachers/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0],
            {
                "id": str(teacher.id),
                "first_name": "Joanie",
                "last_name": "Cunningham",
            },
        )

    def test_api_admin_teacher_retrieve(self):
        """Admin users should be able to get a teacher."""
        teacher = factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get(f"/api/v1.0/admin/teachers/{teacher.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(teacher.id),
                "first_name": "Joanie",
                "last_name": "Cunningham",
            },
        )

    def test_api_admin_teacher_create(self):
        """Admin users should be able to create a new teacher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.post(
            "/api/v1.0/admin/teachers/",
            data={"first_name": "Joanie", "last_name": "Cunningham"},
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Teacher.objects.count(), 1)
        self.assertEqual(response.json()["first_name"], "Joanie")
        self.assertEqual(response.json()["last_name"], "Cunningham")

    def test_api_admin_teacher_update(self):
        """Admin users should be able to update an existing teacher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        teacher = factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        response = self.client.put(
            f"/api/v1.0/admin/teachers/{teacher.id}/",
            content_type="application/json",
            data={"first_name": "Arthur", "last_name": "Fonzarelli"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        teacher.refresh_from_db()
        self.assertEqual(teacher.first_name, "Arthur")
        self.assertEqual(teacher.last_name, "Fonzarelli")

    def test_api_admin_teacher_partial_update(self):
        """Admin users should be able to partially update an existing teacher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        teacher = factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        response = self.client.patch(
            f"/api/v1.0/admin/teachers/{teacher.id}/",
            content_type="application/json",
            data={"first_name": "Richie"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        teacher.refresh_from_db()
        self.assertEqual(teacher.first_name, "Richie")

    def test_api_admin_teacher_delete(self):
        """Admin users should be able to delete an existing teacher."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        teacher = factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        self.assertEqual(models.Teacher.objects.count(), 1)

        response = self.client.delete(f"/api/v1.0/admin/teachers/{teacher.id}/")
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(models.Teacher.objects.count(), 0)

    def test_api_admin_teacher_list_ordering_first_name(self):
        """Verify teacher list can be ordered by first_name."""
        factories.TeacherFactory(first_name="Richie", last_name="Cunningham")
        factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        factories.TeacherFactory(first_name="Marsha", last_name="Simms")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Test ascending order
        response = self.client.get("/api/v1.0/admin/teachers/?ordering=first_name")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        first_names = [teacher["first_name"] for teacher in results]
        self.assertEqual(first_names, ["Joanie", "Marsha", "Richie"])

        # Test descending order
        response = self.client.get("/api/v1.0/admin/teachers/?ordering=-first_name")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        first_names = [teacher["first_name"] for teacher in results]
        self.assertEqual(first_names, ["Richie", "Marsha", "Joanie"])

    def test_api_admin_teacher_list_ordering_last_name(self):
        """Verify teacher list can be ordered by last_name."""
        factories.TeacherFactory(first_name="Arthur", last_name="Fonzarelli")
        factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        factories.TeacherFactory(first_name="Marsha", last_name="Simms")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Test ascending order
        response = self.client.get("/api/v1.0/admin/teachers/?ordering=last_name")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        last_names = [teacher["last_name"] for teacher in results]
        self.assertEqual(last_names, ["Cunningham", "Fonzarelli", "Simms"])

        # Test descending order
        response = self.client.get("/api/v1.0/admin/teachers/?ordering=-last_name")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        last_names = [teacher["last_name"] for teacher in results]
        self.assertEqual(last_names, ["Simms", "Fonzarelli", "Cunningham"])

    def test_api_admin_teacher_filter(self):
        """Verify teacher list can be filtered."""
        factories.TeacherFactory(first_name="Arthur", last_name="Fonzarelli")
        factories.TeacherFactory(first_name="Joanie", last_name="Cunningham")
        factories.TeacherFactory(first_name="Marsha", last_name="Simms")
        factories.TeacherFactory(first_name="Richie", last_name="Cunningham")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Test filtering by last_name
        response = self.client.get("/api/v1.0/admin/teachers/?query=Cunning")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()["results"]), 2)
        first_names = [teacher["first_name"] for teacher in response.json()["results"]]
        last_names = [teacher["last_name"] for teacher in response.json()["results"]]
        self.assertEqual(first_names, ["Joanie", "Richie"])
        self.assertEqual(last_names, ["Cunningham", "Cunningham"])

        # Test filtering by first_name
        response = self.client.get("/api/v1.0/admin/teachers/?query=ar")
        self.assertEqual(len(response.json()["results"]), 2)
        first_names = [teacher["first_name"] for teacher in response.json()["results"]]
        last_names = [teacher["last_name"] for teacher in response.json()["results"]]
        self.assertEqual(first_names, ["Arthur", "Marsha"])
        self.assertEqual(last_names, ["Fonzarelli", "Simms"])
