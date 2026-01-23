"""Test suite on offering deep link model for organizations and offerings"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core import enums, factories, models


class OfferingDeepLinkModelTestCase(TestCase):
    """Test suite on offering deep links model for organizations and offerings"""

    def test_models_offering_deeplink_only_for_product_type_credential(self):
        """
        It should not be possible to create a deep link for a product type other than
        credential
        """
        for product_type, _ in enums.PRODUCT_TYPE_CHOICES:
            if product_type == enums.PRODUCT_TYPE_CREDENTIAL:
                continue

            with self.subTest(product_type=product_type):
                with self.assertRaises(ValidationError) as context:
                    factories.OfferingDeepLinkFactory(
                        offering__product__type=product_type
                    )

                    self.assertTrue(
                        "Only product type credential are allowed to have deeplinks"
                        in str(context.exception)
                    )

    def test_models_offering_deeplink_unique_together_organization_per_offering(self):
        """
        It should not be possible to create two instances with the same offering and
        organization with different deep link values. It should always be one organization
        for one offering.
        """
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(organizations=[organization])

        factories.OfferingDeepLinkFactory(
            organization=organization,
            offering=offering,
            deep_link="https://test-deeplink-1.com/",
        )

        with self.assertRaises(ValidationError) as context:
            factories.OfferingDeepLinkFactory(
                organization=organization,
                offering=offering,
                deep_link="https://test-deeplink-2.com/",
            )

        self.assertTrue(
            "Offering Deep Link with this Organization and Offering already exists."
            in str(context.exception)
        )

    def test_models_offering_deeplink_is_unique(self):
        """
        It should not be possible that two organizations have the same deep link.
        They should all have unique deep links.
        """
        [organization_1, organization_2] = factories.OrganizationFactory.create_batch(2)
        offering = factories.OfferingFactory(
            organizations=[organization_1, organization_2]
        )

        factories.OfferingDeepLinkFactory(
            organization=organization_1,
            offering=offering,
            deep_link="https://test-deeplink-1.com/",
        )

        with self.assertRaises(ValidationError) as context:
            factories.OfferingDeepLinkFactory(
                organization=organization_2,
                offering=offering,
                deep_link="https://test-deeplink-1.com/",
            )

        self.assertTrue(
            "Offering Deep Link with this Deep_link already exists"
            in str(context.exception)
        )

    def test_models_offering_deeplink_for_organization_not_related_to_offering(self):
        """
        It should not be possible to create a deep link when the organization is not
        related to the offering.
        """
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory()

        with self.assertRaises(ValidationError) as context:
            factories.OfferingDeepLinkFactory(
                offering=offering,
                organization=organization,
            )

        self.assertTrue(
            "Organization should be related to the offering" in str(context.exception)
        )

    def test_models_offering_deeplink_create(self):
        """
        It should only be possible to create an offering deep link with an organization
        that is related to the offering. Once created, the deep link must set to False
        for `is_active`.
        """
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(organizations=[organization])

        deep_link = models.OfferingDeepLink.objects.create(
            organization=organization,
            offering=offering,
            deep_link="https://test-deeplink.com/",
        )

        self.assertTrue(models.OfferingDeepLink.objects.count())
        self.assertFalse(deep_link.is_active)
