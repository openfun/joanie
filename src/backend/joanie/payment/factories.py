"""
Payment application factories
"""
import random
import string
from decimal import Decimal as D

import factory.fuzzy
from djmoney.money import Money

from joanie.core.factories import UserFactory

from ..core.factories import OrderFactory
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


class InvoiceFactory(factory.django.DjangoModelFactory):
    """A factory to create an invoice"""

    class Meta:
        """Meta"""

        model = models.Invoice

    recipient_address = factory.Faker("address")
    recipient_name = factory.Faker("name")
    order = factory.SubFactory(OrderFactory)

    @factory.lazy_attribute
    def total(self):
        """
        Return a Money object with a random value less than
        the invoice total amount.
        """
        amount = D(random.randrange(int(self.order.total.amount * 100))) / 100  # nosec
        return Money(amount, self.order.total.currency)


class TransactionFactory(factory.django.DjangoModelFactory):
    """A factory to create a transaction"""

    class Meta:
        """Meta"""

        model = models.Transaction

    reference = factory.LazyAttributeSequence(
        lambda t, n: f"{'ref' if t.total.amount < 0 else 'pay'}_{n:05d}"
    )
    invoice = factory.SubFactory(InvoiceFactory)

    @factory.lazy_attribute
    def total(self):
        """
        Return a Money object with a random value less than
        the invoice total amount.
        """
        amount = (
            D(random.randrange(int(self.invoice.total.amount * 100))) / 100  # nosec
        )
        return Money(amount, self.invoice.total.currency)


class BillingAddressDictFactory(factory.DictFactory):
    """
    Return a billing address dictionary
    """

    address = factory.Faker("street_address")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    postcode = factory.Faker("postcode")
