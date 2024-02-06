"""Factory classes for generating fake data for testing."""
import factory
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, registry

from joanie.edx_imports import edx_models

faker = Faker()
engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
session = Session(engine)
registry().metadata.create_all(engine)


class EdxUniversityFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX universities.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.University
        sqlalchemy_session = session

    id = factory.Faker("pyint")
    name = factory.Faker("company")
    slug = factory.Faker("slug")
    code = factory.Faker("pystr")
    logo = factory.Faker("file_name")
    description = factory.Faker("sentence")
    detail_page_enabled = True
    score = factory.Faker("pyint")
    short_name = factory.Faker("company")
    is_obsolete = False
    prevent_auto_update = False
    partnership_level = factory.Faker("pystr")
