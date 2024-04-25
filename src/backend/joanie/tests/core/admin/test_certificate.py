"""
Test suite for admin certificate viewset search with required organization filter
and search fields with learners values (email, first name,username)
"""

import random
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from joanie.core.enums import ORDER_STATE_VALIDATED
from joanie.core.factories import (
    CourseProductRelationFactory,
    EnrollmentCertificateFactory,
    OrderCertificateFactory,
    OrderFactory,
    OrganizationFactory,
    UserFactory,
)


class CertificateAdminTestCase(TestCase):
    """
    Test suite for admin certificate viewset search fields and with required organization filter.
    """

    def setUp(self):
        """
        Set up data for every tests of this class.
        The Certificate view of the admin django backoffice requires to set a specific
        organization to search through certificates first. It allows to add some additional
        query string in the search bar about the learner to filter out even more (first_name,
        email, username).
        """
        # Create admin user who will request
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=self.admin_user.username, password="password")

        # Certificate through order
        self.learner_1 = UserFactory(
            username="John_Doe", first_name="John Doe", email="user1@example.com"
        )
        self.organization_1 = OrganizationFactory()
        cpr = CourseProductRelationFactory(organizations=[self.organization_1])
        order = OrderFactory(
            owner=self.learner_1,
            product=cpr.product,
            course=cpr.course,
            state=ORDER_STATE_VALIDATED,
        )
        self.certificate_order = OrderCertificateFactory(order=order)

        # Certificate through enrollment
        self.learner_2 = UserFactory(
            username="Marsha_A", first_name="Marsha A", email="user2@example.com"
        )
        self.organization_2 = OrganizationFactory()
        self.certificate_enrollment = EnrollmentCertificateFactory(
            enrollment__user=self.learner_2,
            organization=self.organization_2,
            enrollment__is_active=True,
        )

    def test_admin_certificate_changelist_search_without_required_filter__organization(
        self,
    ):
        """
        When we get on the certificate view of the django admin backoffice, we should find
        no result until we apply the required organization filter. In this case, where
        no organization is set in the required organization filter, we should find 0 result
        and a text mentioning the steps on how to get results.
        """
        certificate_search_url = reverse("admin:core_certificate_changelist")

        response = self.client.get(certificate_search_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed("admin/core/certificate/change_list.html")
        self.assertContains(
            response,
            "To get results, choose an organization on the right first, "
            "then type the username of the student in the search bar.",
        )
        self.assertContains(response, "0 of 0 selected")

    def test_admin_certificate_changelist_search_by_organization(self):
        """
        When we filter with an organization, we should find certificate results from the
        organization.
        """
        certificate_search_url = reverse("admin:core_certificate_changelist")
        search_parameters = {"organization__pk__exact": str(self.organization_1.id)}

        response = self.client.get(certificate_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed("admin/core/certificate/change_list.html")
        self.assertContains(response, str(self.learner_1.username))
        self.assertContains(response, str(self.organization_1))
        self.assertContains(response, str(self.certificate_order.order))
        # Make sure that the certificate of the other organization are not in results
        self.assertNotContains(response, str(self.organization_2))
        self.assertNotContains(response, str(self.certificate_enrollment.enrollment))
        self.assertNotContains(response, str(self.learner_2.username))
        # showing that there is 1 result to tick
        self.assertContains(response, "0 of 1 selected")

    def test_admin_certificate_changelist_search_with_user_values_not_linked_to_organization(
        self,
    ):
        """
        When we apply the required organization filter with user exact values that is not linked
        to the organization, we should not find certificate result.
        """
        certificate_search_url = reverse("admin:core_certificate_changelist")
        selected_string_search = random.choice(
            [
                str(self.learner_2.first_name),
                str(self.learner_2.email),
                str(self.learner_2.username),
            ]
        )
        search_parameters = {
            "q": selected_string_search,
            "organization__pk__exact": str(self.organization_1.id),
        }

        response = self.client.get(certificate_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, str(self.organization_2))
        self.assertNotContains(response, str(self.certificate_enrollment.enrollment))
        self.assertNotContains(response, str(self.certificate_order.order))
        # showing that there is no result to tick
        self.assertContains(response, "0 of 0 selected")
        # Although, they should be present in the search bar and filter box
        self.assertContains(response, selected_string_search)
        self.assertContains(response, str(self.organization_1))

    def test_admin_certificate_changelist_search_with_user_values_linked_to_organization(
        self,
    ):
        """
        When we apply the required organization filter with a user's value that is linked
        to the organization, we should find certificate results.
        """
        certificate_search_url = reverse("admin:core_certificate_changelist")
        search_parameters = {
            "q": str(self.learner_1.username),
            "organization__pk__exact": str(self.organization_1.id),
        }
        response = self.client.get(certificate_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, str(self.certificate_order.order))
        # showing that there is 1 result to tick
        self.assertContains(response, "0 of 1 selected")
        # Make sure that the certificate from the other organization are not in results
        self.assertNotContains(response, str(self.organization_2))
        self.assertNotContains(response, str(self.certificate_enrollment.enrollment))

    def test_admin_certificate_changelist_search_certificate_enrollments(
        self,
    ):
        """
        When we apply the required organization filter with a user's value that is linked
        to the organization, we should find certificate results.
        """
        certificate_search_url = reverse("admin:core_certificate_changelist")
        selected_string_search = random.choice(
            [
                str(self.learner_2.first_name),
                str(self.learner_2.email),
                str(self.learner_2.username),
            ]
        )
        search_parameters = {
            "q": selected_string_search,
            "organization__pk__exact": str(self.organization_2.id),
        }

        response = self.client.get(certificate_search_url, search_parameters)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, str(self.certificate_enrollment.enrollment))
        self.assertContains(response, selected_string_search)
        # Showing that there is 1 result to tick
        self.assertContains(response, "0 of 1 selected")
        # Make sure that the certificates of the other organization are not in results
        self.assertNotContains(response, str(self.certificate_order.order))
        self.assertNotContains(response, str(self.organization_1))
