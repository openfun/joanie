"""Payplug objects factories"""
import string

import factory
import factory.fuzzy
import payplug


class PayplugBillingFactory(factory.Factory):
    """A factory to create a Payplug billing object"""

    class Meta:
        """Meta"""

        model = payplug.resources.Payment.Billing

    address1 = factory.Faker("street_address")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    postcode = factory.Faker("postcode")


class PayplugCardFactory(factory.Factory):
    """A factory to create a Payplug card object"""

    class Meta:
        """Meta"""

        model = payplug.resources.Payment.Card

    id = None
    brand = factory.Faker("credit_card_provider")
    country = factory.Faker("country_code")
    exp_month = factory.Faker("credit_card_expire", date_format="%m")
    exp_year = factory.Faker("credit_card_expire", date_format="%Y")
    last4 = factory.fuzzy.FuzzyText(length=4, chars=string.digits)


class PayplugHostedPaymentFactory(factory.Factory):
    """A factory to create a Payplug hosted payment object"""

    class Meta:
        """Meta"""

        model = payplug.resources.Payment.HostedPayment

    payment_url = factory.Faker("url")


class PayplugPaymentFactory(factory.Factory):
    """A factory to create a Payplug payment resource"""

    class Meta:
        """Meta"""

        model = payplug.resources.Payment

    id = factory.Sequence(lambda n: f"pay_{n:05d}")
    amount = factory.fuzzy.FuzzyInteger(low=0, high=999999)
    billing = factory.SubFactory(PayplugBillingFactory)
    card = factory.SubFactory(PayplugCardFactory)
    failure = None
    hosted_payment = factory.SubFactory(PayplugHostedPaymentFactory)
    is_paid = False
    is_refunded = False


class PayplugRefundFactory(factory.Factory):
    """A factory to create a Payplug refund resource."""

    class Meta:
        """Meta"""

        model = payplug.resources.Refund

    id = factory.Sequence(lambda n: f"ref_{n:05d}")
    amount = factory.fuzzy.FuzzyInteger(low=0, high=999999)
    payment_id = factory.Sequence(lambda n: f"pay_{n:05d}")
