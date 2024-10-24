"""Test suite for the management command 'create_demo'"""

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from joanie.core import factories, models
from joanie.demo.defaults import NB_DEV_OBJECTS


class CreateDevDemoTestCase(TestCase):
    """Test case for the management command 'create_demo'"""

    @override_settings(DEBUG=True)
    def test_commands_create_dev_demo(self):
        """The create_dev_demo management command should create objects as expected."""
        factories.UserFactory(
            username="admin", email="admin@example.com", password="admin"
        )

        call_command("create_dev_demo")

        nb_users = models.User.objects.count()
        expected_nb_users = 1  # admin
        expected_nb_users += 5  # other organization owners
        expected_nb_users += 1  # organization_owner
        expected_nb_users += 1  # student_user
        expected_nb_users += 1  # second_user
        self.assertEqual(nb_users, expected_nb_users)
        nb_product_certificate = NB_DEV_OBJECTS["product_certificate"]
        nb_product_certificate += 1  # product_certificate_enrollment
        nb_product_certificate += 1  # create_product_purchased (type CERTIFICATE)
        nb_product_certificate += (
            1  # create_product_certificate_purchased_with_certificate
        )

        nb_product_credential = NB_DEV_OBJECTS["product_credential"]
        nb_product_credential += (
            1  # create_product_credential_purchased_with_certificate
        )
        nb_product_credential += (
            1  # create_product_credential_purchased with unsigned contract
        )
        nb_product_credential += (
            1  # create_product_credential_purchased with learner signed
        )
        nb_product_credential += (
            1  # create_product_credential_purchased with fully signed contract
        )
        nb_product_credential += (
            1  # create_product_credential_purchased with installment payment failed
        )
        nb_product_credential += 13  # one order of each state

        nb_product = nb_product_credential + nb_product_certificate
        nb_product += 1  # Become a certified botanist gradeo
        self.assertEqual(models.Product.objects.count(), nb_product)

        nb_organization = 1  # The school of glory
        self.assertEqual(models.Organization.objects.count(), nb_organization)

        nb_courses = NB_DEV_OBJECTS["course"]
        nb_courses += (
            4  # Become a certified botanist gradeo: 1 course, 3 target courses
        )
        # product credential have 2 target courses and 1 course
        nb_courses += nb_product_credential * 3
        # product certificate 1 course and no target courses
        nb_courses += nb_product_certificate * 1
        nb_courses += 1  # enrollment_certificate
        self.assertEqual(models.Course.objects.count(), nb_courses)

        nb_enrollment = 1  # product_certificate_enrollment
        nb_enrollment += 1  # product_certificate_order
        nb_enrollment += 1  # product_certificate_order_certificate
        nb_enrollment += 1  # enrollment_certificate
        self.assertEqual(models.Enrollment.objects.count(), nb_enrollment)

        nb_certificate = 1  # enrollment_certificate
        nb_certificate += 1  # product_certificate_order_certificate
        nb_certificate += 1  # create_product_credential_purchased_with_certificate
        self.assertEqual(models.Certificate.objects.count(), nb_certificate)
