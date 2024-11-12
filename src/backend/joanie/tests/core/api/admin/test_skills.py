"""Tests for the Skill Admin API endpoints."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class SkillAdminApiTest(BaseAPITestCase):
    """Test for the Admin SkillViewSet."""

    maxDiff = None

    def test_api_admin_skill_list_anonymous(self):
        """Anonymous users should not be able to list skills."""
        response = self.client.get("/api/v1.0/admin/skills/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_skill_list_non_admin(self):
        """Non admin users should not be able to list skills."""
        user = factories.UserFactory()
        self.client.login(username=user.username, password="password")
        response = self.client.get("/api/v1.0/admin/skills/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_skill_list_admin(self):
        """Admin users should be able to list skills."""
        factories.SkillFactory(title="Python")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get("/api/v1.0/admin/skills/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["title"], "Python")

    def test_api_admin_skill_retrieve(self):
        """Admin users should be able to get a skill."""
        skill = factories.SkillFactory(title="Python")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get(f"/api/v1.0/admin/skills/{skill.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "id": str(skill.id),
                "title": "Python",
            },
        )

    def test_api_admin_skill_retrieve_localized(self):
        """Admin users should be able to get a localized skill."""
        skill = factories.SkillFactory(title="Unit testing")
        skill.translations.create(language_code="fr-fr", title="Test unitaire")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get(f"/api/v1.0/admin/skills/{skill.id}/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # The default language is English
        self.assertEqual(response.json()["title"], "Unit testing")

        # Change the language to French
        response = self.client.get(
            f"/api/v1.0/admin/skills/{skill.id}/",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
        )

        self.assertEqual(response.json()["title"], "Test unitaire")

        # Unknown language should fallback to the default language (English)
        response = self.client.get(
            f"/api/v1.0/admin/skills/{skill.id}/",
            HTTP_ACCEPT_LANGUAGE="es-es",
        )
        self.assertEqual(response.json()["title"], "Unit testing")

    def test_api_admin_skill_create(self):
        """Admin users should be able to create a new skill."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.post(
            "/api/v1.0/admin/skills/",
            content_type="application/json",
            data={"title": "Python"},
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(models.Skill.objects.count(), 1)
        self.assertEqual(response.json()["title"], "Python")

    def test_api_admin_skill_update(self):
        """Admin users should be able to update an existing skill."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        skill = factories.SkillFactory(title="JS")
        response = self.client.put(
            f"/api/v1.0/admin/skills/{skill.id}/",
            content_type="application/json",
            data={"title": "JavaScript"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        skill.refresh_from_db()
        self.assertEqual(skill.title, "JavaScript")

    def test_api_admin_skill_partial_update(self):
        """Admin users should be able to partially update an existing skill."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        skill = factories.SkillFactory(title="JS")
        response = self.client.patch(
            f"/api/v1.0/admin/skills/{skill.id}/",
            content_type="application/json",
            data={"title": "JavaScript"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        skill.refresh_from_db()
        self.assertEqual(skill.title, "JavaScript")

    def test_api_admin_skill_partial_update_localized(self):
        """Admin users should be able to partially update an existing skill in a given language."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        skill = factories.SkillFactory(title="Unit testing")

        response = self.client.patch(
            f"/api/v1.0/admin/skills/{skill.id}/",
            content_type="application/json",
            HTTP_ACCEPT_LANGUAGE="fr-fr",
            data={"title": "Test unitaire"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        skill.refresh_from_db()

        self.assertEqual(skill.title, "Unit testing")
        self.assertEqual(
            skill.safe_translation_getter("title", language_code="fr-fr"),
            "Test unitaire",
        )
        self.assertEqual(
            skill.safe_translation_getter("title", language_code="de-de"),
            "Unit testing",
        )

    def test_api_admin_skill_delete(self):
        """Admin users should be able to delete an existing skill."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        skill = factories.SkillFactory(title="Java")
        self.assertEqual(models.Skill.objects.count(), 1)

        response = self.client.delete(f"/api/v1.0/admin/skills/{skill.id}/")
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(models.Skill.objects.count(), 0)

    def test_api_admin_skill_list_ordering(self):
        """Verify skill list can be ordered by title translation."""
        factories.SkillFactory(title="VueJS")
        factories.SkillFactory(title="React")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Test ascending order
        response = self.client.get(
            "/api/v1.0/admin/skills/?ordering=translations__title"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        titles = [skill["title"] for skill in results]
        self.assertEqual(titles, ["React", "VueJS"])

        # Test descending order
        response = self.client.get(
            "/api/v1.0/admin/skills/?ordering=-translations__title"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        titles = [skill["title"] for skill in results]
        self.assertEqual(titles, ["VueJS", "React"])

    def test_api_admin_skill_filter(self):
        """Verify skill list can be filtered."""
        factories.SkillFactory(title="VueJS")
        factories.SkillFactory(title="React")

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get("/api/v1.0/admin/skills/?query=Vue")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["title"], "VueJS")
