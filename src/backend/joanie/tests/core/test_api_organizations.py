"""
Test suite for Organization API endpoint.
"""
import random
from unittest import mock

from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase


class OrganizationApiTest(BaseAPITestCase):
    """
    Test suite for Organization API endpoint.
    """

    def test_api_organization_list_anonymous(self):
        """
        Anonymous users should not be able to list organizations.
        """
        factories.OrganizationFactory()
        response = self.client.get("/api/v1.0/organizations/")

        self.assertEqual(response.status_code, 401)
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

        with self.assertNumQueries(47):
            response = self.client.get(
                "/api/v1.0/organizations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
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
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        with mock.patch.object(
            models.Organization, "get_abilities", return_value={"foo": "bar"}
        ) as mock_abilities:
            response = self.client.get(
                "/api/v1.0/organizations/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
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
                    }
                ],
            },
        )
        mock_abilities.called_once_with(user)

    def test_api_organization_get_anonymous(self):
        """
        Anonymous users should not be allowed to get an organization through its id.
        """
        organization = factories.OrganizationFactory()

        response = self.client.get(f"/api/v1.0/organizations/{organization.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_organization_get_authenticated_no_access(self):
        """
        Authenticated users should not be able to get an organization through its id
        if they have no access to it.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organization_get_authenticated_with_access(self, _):
        """
        Authenticated users should be able to get an organization through its id
        if they have access to it.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertTrue(content.pop("abilities")["get"])
        self.assertEqual(
            content,
            {
                "code": organization.code,
                "id": str(organization.id),
                "logo": "_this_field_is_mocked",
                "title": organization.title,
            },
        )

    def test_api_organization_create_anonymous(self):
        """
        Anonymous users should not be able to create an organization.
        """
        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post("/api/v1.0/organizations/", data=data)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(models.Organization.objects.exists())

    def test_api_organization_create_authenticated(self):
        """
        Authenticated users should not be able to create an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.post(
            "/api/v1.0/organizations/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(models.Organization.objects.exists())

    def test_api_organization_update_anonymous(self):
        """
        Anonymous users should not be able to update an organization.
        """
        organization = factories.OrganizationFactory()

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/", data=data
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_update_authenticated_no_access(self):
        """
        Authenticated users should not be able to update an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_update_authenticated_with_access(self):
        """
        Authenticated users with owner role should not be
        able to update an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=enums.OWNER,
        )

        data = {
            "code": "ORG-001",
            "title": "Organization 001",
        }

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"detail": 'Method "PUT" not allowed.'})

        organization.refresh_from_db()
        for key, value in data.items():
            self.assertNotEqual(value, getattr(organization, key))

    def test_api_organization_delete_anonymous(self):
        """
        Anonymous users should not be able to delete an organization.
        """
        organization = factories.OrganizationFactory()

        response = self.client.delete(f"/api/v1.0/organizations/{organization.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(models.Organization.objects.count(), 1)

    def test_api_organization_delete_authenticated_no_access(self):
        """
        Authenticated users should not be able to delete an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Organization.objects.count(), 1)

    def test_api_organization_delete_authenticated_with_access(self):
        """
        Authenticated users with owner role should not be able
        to delete an organization.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=enums.OWNER,
        )

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Organization.objects.count(), 1)

    def test_api_organization_contracts_signature_link_success(self):
        """
        Authenticated users with owner role should be able to sign contracts in bulk.
        """
        student_user = factories.UserFactory(email="johnnydo@example.fr")
        factories.AddressFactory.create(owner=student_user)
        order = factories.OrderFactory(
            owner=student_user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )
        InvoiceFactory(order=order)
        order.validate()
        order.submit_for_signature(student_user)
        order.contract.submitted_for_signature_on = timezone.now()
        order.contract.student_signed_on = timezone.now()
        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?requestToken=",
            content["invitation_link"],
        )

    def test_api_organization_contracts_signature_link_specified_ids(self):
        """
        When passing a list of contract ids,
        only the contracts with these ids should be signed.
        """
        student_user = factories.UserFactory(email="johnnydo@example.fr")
        factories.AddressFactory.create(owner=student_user)
        order = factories.OrderFactory(
            owner=student_user,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )
        InvoiceFactory(order=order)
        order.validate()
        order.submit_for_signature(student_user)
        order.contract.submitted_for_signature_on = timezone.now()
        order.contract.student_signed_on = timezone.now()

        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"contract_ids": [order.contract.id]},
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?requestToken=",
            content["invitation_link"],
        )

    def test_api_organization_contracts_signature_link_no_contracts(self):
        """A 404 should be returned if no contract is available to sign."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user, organization=organization, role=enums.OWNER
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        assert response.json() == {
            "detail": "No contract to sign for this organization."
        }
