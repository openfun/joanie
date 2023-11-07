"""
Badge application factories
"""

import factory

from joanie.badges import models
from joanie.core.factories import UserFactory


class BadgeFactory(factory.django.DjangoModelFactory):
    """
    A factory to generate a badge from a provider.
    """

    class Meta:
        model = models.Badge

    name = factory.Faker("slug")
    description = factory.Faker("sentence")
    iri = factory.Faker("uri")
    provider = factory.fuzzy.FuzzyChoice(
        models.get_badge_provider_choices().choices, getter=lambda c: c[0]
    )


class IssuedBadgeFactory(factory.django.DjangoModelFactory):
    """
    A factory to issue a badge from a provider.
    """

    class Meta:
        model = models.IssuedBadge

    iri = factory.Faker("uri")
    resource_link = factory.Faker("uri")
    user = factory.SubFactory(UserFactory)
    badge = factory.SubFactory(BadgeFactory)
    assertion = factory.Dict(
        {
            "id": factory.Faker("uuid4"),
            "image": factory.Faker("uri"),
            "json": factory.Faker("uri"),
            "recipient": factory.Faker("email"),
            "status": factory.Faker(
                "random_element", elements=["accepted", "issued", "refused"]
            ),
        }
    )
