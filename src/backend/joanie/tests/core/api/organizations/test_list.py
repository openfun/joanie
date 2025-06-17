"""
Test suite for Organization list API endpoint.
"""

import uuid
from http import HTTPStatus
from unittest import mock

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiListTest(BaseAPITestCase):
    """
    Test suite for Organization list API endpoint.
    """

    def test_api_organization_list_anonymous(self):
        """
        Anonymous users should not be able to list organizations.
        """
        factories.OrganizationFactory()
        response = self.client.get("/api/v1.0/organizations/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_list_authenticated_queries(self):
        """
        Authenticated users should only see the organizations to which they have access.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        factories.OrganizationFactory()
        organizations = factories.OrganizationFactory.create_batch(3)
        factories.UserOrganizationAccessFactory(
            user=user, organization=organizations[0]
        )
        factories.UserOrganizationAccessFactory(
            user=user, organization=organizations[1]
        )

        with self.assertNumQueries(49):
            response = self.client.get(
                "/api/v1.0/organizations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        results = response.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertCountEqual(
            [item["id"] for item in results],
            [str(organization.id) for organization in organizations[:2]],
        )
        self.assertTrue(all(item["abilities"]["get"] for item in results))

    def test_api_organization_list_authenticated_format(self):
        """
        Authenticated users should only see the organizations to which they have access.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        factories.OrganizationFactory()
        organization = factories.OrganizationFactory()
        address_organization = factories.OrganizationAddressFactory(
            organization=organization, is_main=True, is_reusable=True
        )
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        with mock.patch.object(
            models.Organization, "get_abilities", return_value={"foo": "bar"}
        ) as mock_abilities:
            response = self.client.get(
                "/api/v1.0/organizations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "abilities": {"foo": "bar"},
                        "code": organization.code,
                        "id": str(organization.id),
                        "logo": {
                            "filename": organization.logo.name,
                            "src": f"http://testserver{organization.logo.url}.1x1_q85.webp",
                            "srcset": (
                                f"http://testserver{organization.logo.url}.1024x1024_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                "1024w, "
                                f"http://testserver{organization.logo.url}.512x512_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                "512w, "
                                f"http://testserver{organization.logo.url}.256x256_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                "256w, "
                                f"http://testserver{organization.logo.url}.128x128_q85_crop-scale_upscale.webp "  # pylint: disable=line-too-long
                                "128w"
                            ),
                            "width": 1,
                            "height": 1,
                            "size": organization.logo.size,
                        },
                        "title": organization.title,
                        "address": {
                            "id": str(address_organization.id),
                            "address": address_organization.address,
                            "city": address_organization.city,
                            "postcode": address_organization.postcode,
                            "country": address_organization.country,
                            "first_name": address_organization.first_name,
                            "last_name": address_organization.last_name,
                            "title": address_organization.title,
                            "is_main": True,
                        },
                        "enterprise_code": organization.enterprise_code,
                        "activity_category_code": (organization.activity_category_code),
                        "contact_email": organization.contact_email,
                        "contact_phone": organization.contact_phone,
                        "dpo_email": organization.dpo_email,
                    }
                ],
            },
        )
        mock_abilities.called_once_with(user)

    def test_api_organization_list_filtered_by_offer_id(self):
        """
        Authenticated users should only see the organizations to which they have access
        and should be able to filter them by offer.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        factories.OrganizationFactory()
        organizations = factories.OrganizationFactory.create_batch(3)
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

        # Create an offer with the first organization
        offer = factories.OfferFactory(organizations=[organizations[0]])

        # - Without filter all organizations with access should be returned
        response = self.client.get(
            "/api/v1.0/organizations/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        # - With filter only organizations linked to the offer should be returned
        response = self.client.get(
            f"/api/v1.0/organizations/?offer_id={offer.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(organizations[0].id))

        # - If the offer does not exist, no organization should be returned
        response = self.client.get(
            f"/api/v1.0/organizations/?offer_id={uuid.uuid4()}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_organization_list_filtered_by_invalid_offer_id(self):
        """
        If the user tries to filter organizations by an invalid offer
        id, a bad request should be returned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        factories.OrganizationFactory()
        organizations = factories.OrganizationFactory.create_batch(3)
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

        response = self.client.get(
            "/api/v1.0/organizations/?offer_id=invalid_id",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"offer_id":["Enter a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )
