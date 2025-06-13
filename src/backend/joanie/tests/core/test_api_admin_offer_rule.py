"""
Test suite for OfferRule Admin API.
"""

from datetime import timedelta
from http import HTTPStatus

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from joanie.core import factories, models


class OfferRuleAdminApiTest(TestCase):
    """
    Test suite for OfferRule Admin API.
    """

    base_url = "/api/v1.0/admin/course-product-relations"

    # list
    def test_admin_api_offer_rule_list_anonymous(self):
        """
        Anonymous users should not be able to list offer rules.
        """

        relation = factories.CourseProductRelationFactory()
        response = self.client.get(f"{self.base_url}/{relation.id}/offer-rules/")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_offer_rule_list_authenticated(self):
        """
        Authenticated users should be able to list offer rules.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        discount = factories.DiscountFactory(rate=0.3)
        offer_rules = [
            factories.OfferRuleFactory(
                position=i, course_product_relation=relation, discount=discount
            )
            for i in range(3)
        ]

        factories.OfferRuleFactory.create_batch(5)

        with self.assertNumQueries(19):
            response = self.client.get(f"{self.base_url}/{relation.id}/offer-rules/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        expected_return = [
            {
                "id": str(offer_rule.id),
                "description": offer_rule.description,
                "nb_seats": offer_rule.nb_seats,
                "is_active": offer_rule.is_active,
                "is_enabled": offer_rule.is_enabled,
                "nb_available_seats": offer_rule.nb_seats
                - offer_rule.get_nb_binding_orders(),
                "created_on": offer_rule.created_on.isoformat().replace("+00:00", "Z"),
                "can_edit": True,
                "start": None,
                "end": None,
                "discount": {
                    "id": str(discount.id),
                    "amount": None,
                    "rate": 0.3,
                    "is_used": 3,
                },
            }
            for offer_rule in offer_rules
        ]
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"], expected_return)

    def test_admin_api_offer_rule_list_lambda_user(self):
        """
        Non admin user should not be able to request offer rules endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory()

        response = self.client.get(f"{self.base_url}/{relation.id}/offer-rules/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    # details
    def test_admin_api_offer_rule_retrieve_anonymous(self):
        """
        Anonymous users should not be able to request offer rules details.
        """

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)

        response = self.client.get(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_offer_rule_retrieve_authenticated(self):
        """
        Authenticated users should be able to request offer rules details.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
            discount=factories.DiscountFactory(amount=30),
        )

        with self.assertNumQueries(8):
            response = self.client.get(
                f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        expected_return = {
            "id": str(offer_rule.id),
            "description": offer_rule.description,
            "nb_seats": offer_rule.nb_seats,
            "is_active": offer_rule.is_active,
            "is_enabled": offer_rule.is_enabled,
            "nb_available_seats": offer_rule.nb_seats
            - offer_rule.get_nb_binding_orders(),
            "created_on": offer_rule.created_on.isoformat().replace("+00:00", "Z"),
            "can_edit": True,
            "start": None,
            "end": None,
            "discount": {
                "id": str(offer_rule.discount.id),
                "amount": 30,
                "rate": None,
                "is_used": 1,
            },
        }
        self.assertEqual(content, expected_return)

    # create
    def test_admin_api_offer_rule_create_anonymous(self):
        """
        Anonymous users should not be able to create an offer rule.
        """
        relation = factories.CourseProductRelationFactory()

        data = {"nb_seats": 5, "is_active": True}
        response = self.client.post(
            f"{self.base_url}/{relation.id}/offer-rules/",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_offer_rule_create_authenticated_with_nb_seats_is_none(self):
        """
        Authenticated users should be able to create an offer rule and set None for
        `nb_seats`.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        relation = factories.CourseProductRelationFactory()
        data = {
            "nb_seats": None,
            "is_active": True,
        }

        response = self.client.post(
            f"{self.base_url}/{relation.id}/offer-rules/",
            content_type="application/json",
            data=data,
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIsNone(content["nb_seats"])
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertTrue(content["is_enabled"])
        self.assertEqual(models.OfferRule.objects.filter(**data).count(), 1)

    def test_admin_api_offer_rule_create_authenticated(self):
        """
        Authenticated users should be able to request offer rules list.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        data = {
            "nb_seats": 5,
            "is_active": True,
        }
        with self.assertNumQueries(8):
            response = self.client.post(
                f"{self.base_url}/{relation.id}/offer-rules/",
                content_type="application/json",
                data=data,
            )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        content = response.json()
        self.assertEqual(content["nb_seats"], data["nb_seats"])
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(models.OfferRule.objects.filter(**data).count(), 1)

    # update
    def test_admin_api_offer_rule_update_anonymous(self):
        """
        Anonymous users should not be able to update offer rules.
        """

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)

        response = self.client.put(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_offer_rule_update_authenticated(self):
        """
        Authenticated users should be able to update offer rules.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)
        data = {
            "nb_seats": 505,
            "is_active": True,
        }
        with self.assertNumQueries(7):
            response = self.client.put(
                f"{self.base_url}/{relation.id}/offer-rules/{str(offer_rule.id)}/",
                content_type="application/json",
                data=data,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["nb_seats"], data["nb_seats"])
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(models.OfferRule.objects.filter(**data).count(), 1)

    # patch
    def test_admin_api_offer_rule_patch_anonymous(self):
        """
        Anonymous users should not be able to patch offer rules.
        """

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)

        response = self.client.patch(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_admin_api_offer_rule_patch_authenticated(self):
        """
        Authenticated users should be able to patch offer rules.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation, is_active=False
        )
        data = {
            "is_active": True,
        }
        with self.assertNumQueries(7):
            response = self.client.patch(
                f"{self.base_url}/{relation.id}/offer-rules/{str(offer_rule.id)}/",
                content_type="application/json",
                data=data,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["nb_seats"], offer_rule.nb_seats)
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(
            models.OfferRule.objects.filter(
                nb_seats=offer_rule.nb_seats, **data
            ).count(),
            1,
        )

    def test_admin_api_offer_rule_patch_authenticated_empty_nb_seats(self):
        """
        The frontend sends an empty string when the user wants to set the number of seats to None.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation, is_active=False
        )
        data = {
            "nb_seats": "",
            "is_active": True,
        }
        with self.assertNumQueries(5):
            response = self.client.patch(
                f"{self.base_url}/{relation.id}/offer-rules/{str(offer_rule.id)}/",
                content_type="application/json",
                data=data,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["nb_seats"], None)
        self.assertEqual(content["is_active"], data["is_active"])
        self.assertEqual(
            models.OfferRule.objects.filter(
                nb_seats__isnull=True, is_active=data["is_active"]
            ).count(),
            1,
        )

    # delete
    def test_admin_api_offer_rule_delete_anonymous(self):
        """
        Anonymous users should not be able to delete offer rules.
        """

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)

        response = self.client.delete(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        with self.assertNumQueries(0):
            self.assertEqual(
                content["detail"], "Authentication credentials were not provided."
            )

    def test_admin_api_offer_rule_delete_authenticated(self):
        """
        Authenticated users should not be able to delete offer rules.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)
        with self.assertNumQueries(7):
            response = self.client.delete(
                f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(models.OfferRule.objects.filter(id=offer_rule.id).exists())

    def test_admin_api_offer_rule_delete_cannot_edit(self):
        """
        Deleting an offer rule that cannot be edited should fail.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(course_product_relation=relation)
        with self.assertNumQueries(7):
            response = self.client.delete(
                f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(models.OfferRule.objects.filter(id=offer_rule.id).exists())

    def test_admin_api_offer_rule_create_start_date(self):
        """
        Authenticated admin user should be able to create an offer rule and set
        a start and end date.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        data = {
            "start": "2025-06-01T00:00:00Z",
            "end": "",
            "discount_id": "",
            "nb_seats": "",
            "is_active": False,
        }

        response = self.client.post(
            f"{self.base_url}/{relation.id}/offer-rules/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        content = response.json()

        self.assertEqual(content["start"], data["start"])
        self.assertFalse(content["is_active"])

    def test_admin_api_offer_rule_create_start_and_end_date(self):
        """
        Authenticated admin user should be able to create an offer rule and set
        a start and end date.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        data = {
            "start": "2025-06-01T00:00:00Z",
            "end": "2025-06-20T00:00:00Z",
            "nb_seats": 10,
            "is_active": False,
        }

        response = self.client.post(
            f"{self.base_url}/{relation.id}/offer-rules/",
            content_type="application/json",
            data=data,
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        content = response.json()

        self.assertEqual(content["start"], data["start"])
        self.assertEqual(content["end"], data["end"])
        self.assertFalse(content["is_active"])

    def test_admin_api_offer_rule_create_start_date_greater_than_end_date(self):
        """
        Authenticated admin user should not be able to create an offer rule when the
        start date is greater than the end date.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        data = {
            "start": "2025-01-20T00:00:00Z",
            "end": "2025-01-01T00:00:00Z",
        }

        with self.assertRaises(IntegrityError):
            self.client.post(
                f"{self.base_url}/{relation.id}/offer-rules/",
                content_type="application/json",
                data=data,
            )

    def test_admin_api_offer_rule_update_start_and_end_date(self):
        """
        Authenticated admin user can update the start and end date of an existing
        offer rule.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
            start="2025-01-11T00:00:00Z",
            end="2025-01-20T00:00:00Z",
        )

        data = {
            "start": "2025-02-13T00:00:00Z",
            "end": "2025-02-19T00:00:00Z",
        }

        response = self.client.put(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            content_type="application/json",
            data=data,
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(content["start"], data["start"])
        self.assertEqual(content["end"], data["end"])

    def test_admin_api_offer_rule_is_enabled_and_is_active(
        self,
    ):
        """
        When the offer rule is not yet active, even if the dates qualifies for early-birds
        or last minutes sales, the property `is_enabled` should return False. Otherwise,
        when the offer rule is active, the computed value of the property `is_enabled` will
        return True if the datetimes meet the conditions.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        test_cases = [
            {
                "start": None,
                "end": django_timezone.now() + timedelta(days=1),
            },
            {"start": django_timezone.now(), "end": None},
            {
                "start": django_timezone.now() - timedelta(days=1),
                "end": django_timezone.now() + timedelta(days=1),
            },
        ]

        for case in test_cases:
            with self.subTest(start=case["start"], end=case["end"]):
                offer_rule = factories.OfferRuleFactory(
                    course_product_relation=relation,
                    is_active=False,
                    start=case["start"],
                    end=case["end"],
                )

                response = self.client.get(
                    f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
                )

                content = response.json()

                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertFalse(content["is_active"])
                self.assertFalse(content["is_enabled"])

                offer_rule.is_active = True
                offer_rule.save()

                response = self.client.get(
                    f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
                )

                content = response.json()

                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertTrue(content["is_active"])
                self.assertTrue(content["is_enabled"])

    def test_admin_api_offer_rule_is_not_enabled_start_end_outside_datetime_range(
        self,
    ):
        """
        When the offer rule is active but is not yet within the datetime ranges to be enabled,
        it should return False.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        test_cases = [
            {
                "start": None,
                "end": django_timezone.now() - timedelta(days=1),
            },
            {"start": django_timezone.now() + timedelta(days=1), "end": None},
            {
                "start": django_timezone.now() + timedelta(days=1),
                "end": django_timezone.now() + timedelta(days=2),
            },
        ]

        for case in test_cases:
            with self.subTest(start=case["start"], end=case["end"]):
                offer_rule = factories.OfferRuleFactory(
                    course_product_relation=relation,
                    is_active=True,
                    start=case["start"],
                    end=case["end"],
                )

                response = self.client.get(
                    f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
                )

                content = response.json()

                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertTrue(content["is_active"])
                self.assertFalse(content["is_enabled"])

    def test_admin_api_offer_rule_is_active_and_nb_seats_is_enabled(self):
        """
        When the offer rule is active and the number of seats is None,
        `is_enabled` should return the value True. Otherwise, it should
        return False.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
            is_active=True,
            nb_seats=None,
            start=None,
            end=None,
        )

        response = self.client.get(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
        )

        content = response.json()

        self.assertTrue(content["is_enabled"])
        self.assertTrue(content["is_active"])
        self.assertIsNone(content["nb_available_seats"])
        self.assertIsNone(content["nb_seats"])

        offer_rule.is_active = False
        offer_rule.save()

        response = self.client.get(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/"
        )

        content = response.json()

        self.assertFalse(content["is_enabled"])
        self.assertFalse(content["is_active"])
        self.assertIsNone(content["nb_available_seats"])
        self.assertIsNone(content["nb_seats"])

    def test_admin_api_offer_rule_update_discount(self):
        """Authenticated admin user can add a discount on the offer rule."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        discount = factories.DiscountFactory(rate=0.5)
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
        )

        response = self.client.put(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            content_type="application/json",
            data={"discount_id": str(discount.id)},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content["discount"],
            {
                "id": str(discount.id),
                "amount": discount.amount,
                "rate": discount.rate,
                "is_used": 1,
            },
        )

    def test_admin_api_offer_rule_partially_update_discount(self):
        """Authenticated admin user can partially update an existing offer rule's discount."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
            discount=factories.DiscountFactory(rate=0.5),
        )
        new_discount = factories.DiscountFactory(amount=10)

        response = self.client.patch(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            content_type="application/json",
            data={"discount_id": str(new_discount.id)},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(
            content["discount"],
            {
                "id": str(new_discount.id),
                "amount": new_discount.amount,
                "rate": new_discount.rate,
                "is_used": 1,
            },
        )

    def test_admin_api_offer_rule_update_to_remove_discount(self):
        """Authenticated admin user wants to remove the offer rule's discount."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
            discount=factories.DiscountFactory(rate=0.5),
        )

        response = self.client.put(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            content_type="application/json",
            data={"discount_id": None},
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(content["discount"])

    def test_admin_api_offer_rule_update_to_remove_start(self):
        """Authenticated admin user wants to remove the offer rule's discount."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
            discount=factories.DiscountFactory(rate=0.5),
            start=django_timezone.now(),
        )

        response = self.client.put(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            content_type="application/json",
            data={"start": ""},
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(content["start"])
        offer_rule.refresh_from_db()
        self.assertIsNone(offer_rule.start)

    def test_admin_api_offer_rule_add_discount_that_does_not_exist(self):
        """
        Authenticated admin user should not be able to update an offer rule with a discount
        id that does not exist
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=relation,
        )

        response = self.client.put(
            f"{self.base_url}/{relation.id}/offer-rules/{offer_rule.id}/",
            content_type="application/json",
            data={"discount_id": "fake_discount_id"},
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_admin_offer_rule_create_with_discount(self):
        """
        Admin authenticated user should be able to create an offer rule with a discount.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()
        discount = factories.DiscountFactory(rate=0.1)

        response = self.client.post(
            f"{self.base_url}/{relation.id}/offer-rules/",
            content_type="application/json",
            data={
                "nb_seats": "",
                "is_active": True,
                "discount_id": str(discount.id),
                "course_product_relation": str(relation.id),
            },
        )

        content = response.json()

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            content["discount"],
            {
                "id": str(discount.id),
                "amount": discount.amount,
                "rate": discount.rate,
                "is_used": 1,
            },
        )

    def test_api_admin_offer_rule_create_with_fake_discount(self):
        """
        Admin authenticated user should be able not be able to create an offer rule
        with a discount that does not exists.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        relation = factories.CourseProductRelationFactory()

        response = self.client.post(
            f"{self.base_url}/{relation.id}/offer-rules/",
            content_type="application/json",
            data={
                "discount_id": "fake_discount_id",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
