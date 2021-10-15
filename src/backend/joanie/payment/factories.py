"""
Payment application factories
"""
import string

import factory
import factory.fuzzy

from joanie.core.factories import UserFactory

from . import models


class CreditCardFactory(factory.django.DjangoModelFactory):
    """A factory to create a credit card."""

    class Meta:
        """Meta"""

        model = models.CreditCard

    brand = factory.Faker("credit_card_provider")
    expiration_month = factory.Faker("credit_card_expire", date_format="%m")
    expiration_year = factory.Faker("credit_card_expire", date_format="%Y")
    last_numbers = factory.fuzzy.FuzzyText(length=4, chars=string.digits)
    owner = factory.SubFactory(UserFactory)
    title = factory.Faker("name")
    token = factory.Sequence(lambda k: f"card_{k:022d}")
