"""
Test suite for wish API
"""
from http import HTTPStatus

import arrow

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


# pylint: disable=too-many-public-methods
class CourseWishAPITestCase(BaseAPITestCase):
    """Manage user course wish API test case"""

    def test_api_course_wish_get_anonymous(self):
        """An anonymous user should not be able to get a course wish."""
        course = factories.CourseFactory()
        response = self.client.get(f"/api/v1.0/courses/{course.id}/wish/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_wish_get_bad_token(self):
        """It should not be possible to get a course wish with a bad user token."""
        course = factories.CourseFactory()
        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/wish/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json()["code"], "token_not_valid")

    def test_api_course_wish_get_expired_token(self):
        """Get user wish not allowed with user token expired"""
        course = factories.CourseFactory()
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json()["code"], "token_not_valid")

    def test_api_course_wish_get_new_user(self):
        """
        If we try to get a course wish for a user not in db, a new user is created first.
        """
        course = factories.CourseFactory()
        username = "panoramix"
        token = self.get_user_token(username)

        self.assertFalse(models.User.objects.filter(username=username).exists())

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"status": False})
        self.assertTrue(models.User.objects.filter(username=username).exists())

    def test_api_course_wish_unknown_course(self):
        """Get course wish for an unknown course should return a 404."""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory.build()

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_course_wish_get_existing(self):
        """Get existing course wish for a user present in db."""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()
        factories.CourseWishFactory(owner=user, course=course)

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"status": True})

    def test_api_course_wish_get_absent(self):
        """Get absent course wish for a user present in db."""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()

        response = self.client.get(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"status": False})

    def test_api_course_wish_create_anonymous(self):
        """Anonymous users should not be allowed to create a course wish."""
        course = factories.CourseFactory()

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/wish/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_course_wish_create_with_bad_token(self):
        """It should not be possible to create a course wish with a bad user token."""
        course = factories.CourseFactory()

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/wish/",
            HTTP_AUTHORIZATION="Bearer nawak",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json()["code"], "token_not_valid")

    def test_api_course_wish_create_with_expired_token(self):
        """Create user wish not allowed with user token expired"""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json()["code"], "token_not_valid")

    def test_api_course_wish_create_success(self):
        """Logged-in users should be able to create a course wish."""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"status": True})

    def test_api_course_wish_create_success_with_course_code(self):
        """Logged-in users should be able to create a course wish with course code."""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/courses/{course.code}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"status": True})

    def test_api_course_wish_create_existing(self):
        """Trying to create a course wish that already exists should work as if it was created."""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        models.CourseWish.objects.create(course=course, owner=user)

        response = self.client.post(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json(), {"status": True})

    def test_api_course_wish_update_success(self):
        """Updating a wish is not supported."""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        models.CourseWish.objects.create(course=course, owner=user)

        response = self.client.put(
            f"/api/v1.0/courses/{course.id}/wish/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

    def test_api_course_wish_delete_anonymous(self):
        """Anonymous users should not be allowed to delete a wish."""
        user = factories.UserFactory()
        wish = factories.CourseWishFactory.create(owner=user)

        response = self.client.delete(
            f"/api/v1.0/courses/{wish.course.id}/wish/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )
        self.assertTrue(models.CourseWish.objects.exists())

    def test_api_course_wish_delete_bad_token(self):
        """It should not be possible to delete a course wish with a bad user token."""
        user = factories.UserFactory()
        wish = factories.CourseWishFactory.create(owner=user)

        response = self.client.delete(
            f"/api/v1.0/courses/{wish.course.id}/wish/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json()["code"], "token_not_valid")
        self.assertTrue(models.CourseWish.objects.exists())

    def test_api_course_wish_delete_with_expired_token(self):
        """Delete wish is not allowed with expired token."""
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        wish = factories.CourseWishFactory.create(owner=user)

        response = self.client.delete(
            f"/api/v1.0/courses/{wish.course.id}/wish/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json()["code"], "token_not_valid")
        self.assertTrue(models.CourseWish.objects.exists())

    def test_api_course_wish_delete_success(self):
        """Delete course wish is allowed with valid token."""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        wish = factories.CourseWishFactory.create(owner=user)

        response = self.client.delete(
            f"/api/v1.0/courses/{wish.course.id}/wish/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(models.CourseWish.objects.exists())

    def test_api_course_wish_delete_absent(self):
        """Trying to delete course wish that does not exist should work as if it did."""
        course = factories.CourseFactory()
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/wish/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(models.CourseWish.objects.exists())
