"""
Test suite for wish API
"""
import json

import arrow

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


def get_payload(wish):
    """
    According to a CourseWish object, return a valid payload required by
    create wish api routes.
    """
    return {
        "course": wish.course.code,
    }


# pylint: disable=too-many-public-methods
class CourseWishAPITestCase(BaseAPITestCase):
    """Manage user wish API test case"""

    def test_api_wish_get_wish_without_authorization(self):
        """Get user wish not allowed without HTTP AUTH"""
        # Try to get wish without Authorization
        response = self.client.get("/api/v1.0/wishlist/")
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_wish_get_wish_with_bad_token(self):
        """Get user wish not allowed with bad user token"""
        # Try to get wish with bad token
        response = self.client.get(
            "/api/v1.0/wishlist/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_wish_get_wish_with_expired_token(self):
        """Get user wish not allowed with user token expired"""
        # Try to get wish with expired token
        token = self.get_user_token(
            "panoramix",
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        response = self.client.get(
            "/api/v1.0/wishlist/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_wish_get_wish_for_new_user(self):
        """If we try to get wish for a user not in db, we create a new user first"""
        username = "panoramix"
        token = self.get_user_token(username)

        self.assertFalse(models.User.objects.filter(username=username).exists())

        response = self.client.get(
            "/api/v1.0/wishlist/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(len(results), 0)
        self.assertTrue(models.User.objects.filter(username=username).exists())

    def test_api_wish_get_wishes(self):
        """Get wish for a user in db with two wishes linked to him"""
        user = factories.UserFactory()
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        token = self.get_user_token(user.username)
        wish1 = factories.CourseWishFactory.create(owner=user, course=course1)
        wish2 = factories.CourseWishFactory.create(owner=user, course=course2)
        response = self.client.get(
            "/api/v1.0/wishlist/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)

        results = response.data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["course"], course1.code)
        self.assertEqual(results[0]["id"], str(wish1.id))
        self.assertEqual(results[1]["course"], course2.code)
        self.assertEqual(results[1]["id"], str(wish2.id))

    def test_api_wish_get_wishes_filter_by_code(self):
        """Get wish for a user in db with two wishes linked to him"""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        token = self.get_user_token(user.username)
        wish = factories.CourseWishFactory.create(owner=user, course=course)
        factories.CourseWishFactory.create(owner=user)

        get_url = f"/api/v1.0/wishlist/?course_code={course.code}"
        response = self.client.get(get_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 200)

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["course"], course.code)
        self.assertEqual(results[0]["id"], str(wish.id))

    def test_api_wish_get_wish(self):
        """Get wish for a user in db with two wishes linked to him"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        wish = factories.CourseWishFactory.create(owner=user)
        factories.CourseWishFactory.create(owner=user)

        get_url = f"/api/v1.0/wishlist/{wish.id}/"
        response = self.client.get(get_url, HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 200)

        data = response.data
        self.assertEqual(data["course"], wish.course.code)
        self.assertEqual(data["id"], str(wish.id))

    def test_api_wish_create_without_authorization(self):
        """Create/update user wish not allowed without HTTP AUTH"""
        # Try to create wish without Authorization
        wish = factories.CourseWishFactory.build()

        response = self.client.post(
            "/api/v1.0/wishlist/",
            data=get_payload(wish),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_wish_update_without_authorization(self):
        """Update user wish not allowed without HTTP AUTH"""
        # Try to update wish without Authorization
        user = factories.UserFactory()
        wish = factories.CourseWishFactory(owner=user)
        new_wish = factories.CourseWishFactory.build()

        response = self.client.put(
            f"/api/v1.0/wishlist/{wish.id}",
            data=get_payload(new_wish),
            follow=True,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_wish_create_with_bad_token(self):
        """Create wish not allowed with bad user token"""
        # Try to create wish with bad token
        wish = factories.CourseWishFactory.build()

        response = self.client.post(
            "/api/v1.0/wishlist/",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=get_payload(wish),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_wish_update_with_bad_token(self):
        """Update wish not allowed with bad user token"""
        # Try to update wish with bad token
        user = factories.UserFactory()
        wish = factories.CourseWishFactory.create(owner=user)
        new_wish = factories.CourseWishFactory.build()

        response = self.client.put(
            f"/api/v1.0/wishlist/{wish.id}",
            HTTP_AUTHORIZATION="Bearer nawak",
            data=get_payload(new_wish),
            follow=True,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_wish_create_with_expired_token(self):
        """Create user wish not allowed with user token expired"""
        # Try to create wish with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        wish = factories.CourseWishFactory.build()

        response = self.client.post(
            "/api/v1.0/wishlist/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=get_payload(wish),
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_wish_update_with_expired_token(self):
        """Update user wish not allowed with user token expired"""
        # Try to update wish with expired token
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        wish = factories.CourseWishFactory.create(owner=user)
        new_wish = factories.CourseWishFactory.build()

        response = self.client.put(
            f"/api/v1.0/wishlist/{wish.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=get_payload(new_wish),
            follow=True,
            content_type="application/json",
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(content["code"], "token_not_valid")

    def test_api_wish_create_with_bad_payload(self):
        """Create user wish with valid token but bad data"""
        username = "panoramix"
        token = self.get_user_token(username)
        wish = factories.CourseWishFactory.build()
        bad_payload = get_payload(wish).copy()
        bad_payload["course"] = "my very wrong course code"

        response = self.client.post(
            "/api/v1.0/wishlist/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_payload,
        )
        content = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content,
            {"course": ["Object with code=my very wrong course code does not exist."]},
        )
        self.assertFalse(models.User.objects.exists())

        del bad_payload["course"]
        response = self.client.post(
            "/api/v1.0/wishlist/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=bad_payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"course": ["This field is required."]})

    def test_api_wish_update(self):
        """
        User should not be able to update a wish
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        wish = factories.CourseWishFactory(owner=user)

        payload = get_payload(wish)

        response = self.client.put(
            f"/api/v1.0/wishlist/{wish.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data=payload,
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(
            json.loads(response.content),
            {"detail": 'Method "PUT" not allowed.'},
        )

    def test_api_wish_create(self):
        """Create user wish with valid token and data"""
        username = "panoramix"
        token = self.get_user_token(username)
        course = factories.CourseFactory()
        wish = factories.CourseWishFactory.build(course=course)
        payload = get_payload(wish)

        response = self.client.post(
            "/api/v1.0/wishlist/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        # panoramix was a unknown user, so a new user was created
        owner = models.User.objects.get()
        self.assertEqual(owner.username, username)

        # new wish was created for user panoramix
        wish = models.CourseWish.objects.get()
        self.assertEqual(wish.owner, owner)
        self.assertEqual(wish.course.code, payload["course"])

    def test_api_wish_delete_without_authorization(self):
        """Delete wish is not allowed without authorization"""
        user = factories.UserFactory()
        wish = factories.CourseWishFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/wishlist/{wish.id}/",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_wish_delete_with_bad_authorization(self):
        """Delete wish is not allowed with bad authorization"""
        user = factories.UserFactory()
        wish = factories.CourseWishFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/wishlist/{wish.id}/",
            HTTP_AUTHORIZATION="Bearer nawak",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_wish_delete_with_expired_token(self):
        """Delete wish is not allowed with expired token"""
        user = factories.UserFactory()
        token = self.get_user_token(
            user.username,
            expires_at=arrow.utcnow().shift(days=-1).datetime,
        )
        wish = factories.CourseWishFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/wishlist/{wish.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_wish_delete_with_bad_user(self):
        """User token has to match with owner of wish to delete"""
        # create an wish for a user
        wish = factories.CourseWishFactory()
        # now use a token for an other user to update wish
        token = self.get_user_token("panoramix")
        response = self.client.delete(
            f"/api/v1.0/wishlist/{wish.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_wish_delete(self):
        """Delete wish is allowed with valid token"""
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        wish = factories.CourseWishFactory.create(owner=user)
        response = self.client.delete(
            f"/api/v1.0/wishlist/{wish.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(models.CourseWish.objects.exists())
