"""
Payment application factories
"""

import string

import factory.fuzzy

from joanie.core.factories import OrderFactory, UserAddressFactory, UserFactory
from joanie.payment import models


class CreditCardFactory(factory.django.DjangoModelFactory):
    """A factory to create a credit card."""

    class Meta:
        """Meta"""

        model = models.CreditCard
        django_get_or_create = ("token",)

    brand = factory.Faker("credit_card_provider")
    expiration_month = factory.Faker("credit_card_expire", date_format="%m")
    expiration_year = factory.Faker("credit_card_expire", date_format="%Y")
    last_numbers = factory.fuzzy.FuzzyText(length=4, chars=string.digits)
    title = factory.Faker("name")
    token = factory.Sequence(lambda k: f"card_{k:022d}")
    payment_provider = "dummy"
    initial_issuer_transaction_identifier = factory.Faker("uuid4")

    @factory.post_generation
    def owners(self, create, extracted, **kwargs):
        """
        Link owners to the credit card after its creation:
        - link the list of owners passed in "extracted" if any
        """
        if not create or not extracted:
            return

        if extracted:
            for owner in extracted:
                self.add_owner(owner)


class CreditCardOwnershipFactory(factory.django.DjangoModelFactory):
    """A factory to create credit card ownership"""

    class Meta:
        """Meta"""

        model = models.CreditCardOwnership

    owner = factory.SubFactory(UserFactory)
    credit_card = factory.SubFactory(CreditCardFactory)
    is_main = False


class InvoiceFactory(factory.django.DjangoModelFactory):
    """A factory to create an invoice"""

    class Meta:
        """Meta"""

        model = models.Invoice

    recipient_address = factory.SubFactory(UserAddressFactory, is_reusable=False)
    order = factory.SubFactory(OrderFactory)
    total = factory.Faker("pydecimal", left_digits=3, right_digits=2, min_value=0)


class TransactionFactory(factory.django.DjangoModelFactory):
    """A factory to create a transaction"""

    class Meta:
        """Meta"""

        model = models.Transaction

    total = factory.Faker("pydecimal", left_digits=3, right_digits=2, min_value=0)
    reference = factory.LazyAttributeSequence(
        lambda t, n: f"{'ref' if t.total < 0 else 'pay'}_{n:05d}"
    )
    invoice = factory.SubFactory(InvoiceFactory, total=factory.SelfAttribute("..total"))


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
