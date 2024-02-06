"""Factory classes for generating fake data for testing."""
import random

import factory
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, registry

from joanie.core import enums
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


class EdxCourseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX course.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.Course
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: n)
    key = factory.Sequence(lambda n: f"course-v1:edX+{faker.pystr()}+{n}")
    level = factory.Faker("pystr")
    score = factory.Faker("pyint")
    is_active = True
    prevent_auto_update = False
    modification_date = factory.Faker("date_time")
    title = factory.Faker("sentence")
    short_description = factory.Faker("sentence")
    image_url = factory.Faker("file_name")
    session_number = factory.Faker("pyint")
    university_display_name = factory.Faker("sentence")
    show_in_catalog = True
    show_about_page = True
    language = factory.Faker("language_code")


class EdxCourseUniversityRelationFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX course-university relations.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.CourseUniversityRelation
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: n)
    course_id = factory.Faker("pyint")
    university_id = factory.Faker("pyint")
    course = factory.SubFactory(
        EdxCourseFactory, id=factory.SelfAttribute("..course_id")
    )
    university = factory.SubFactory(
        EdxUniversityFactory, id=factory.SelfAttribute("..university_id")
    )
    order = factory.Faker("pyint")


class EdxCourseOverviewFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX course overviews.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.CourseOverview
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: f"course-v1:edX+{faker.pystr()}+{n}")
    display_name = factory.Faker("sentence")
    start = factory.Faker("date_time")
    end = factory.Faker("date_time")
    enrollment_start = factory.Faker("date_time")
    enrollment_end = factory.Faker("date_time")
    created = factory.Faker("date_time")
    _location = factory.Faker("pystr")
    display_number_with_default = factory.Faker("pystr")
    display_org_with_default = factory.Faker("pystr")
    course_image_url = factory.Faker("pystr")
    certificates_show_before_end = factory.Faker("pyint")
    has_any_active_web_certificate = factory.Faker("pyint")
    cert_name_short = factory.Faker("pystr")
    cert_name_long = factory.Faker("pystr")
    mobile_available = factory.Faker("pyint")
    visible_to_staff_only = factory.Faker("pyint")
    _pre_requisite_courses_json = factory.Faker("pystr")
    cert_html_view_enabled = factory.Faker("pyint")
    invitation_only = factory.Faker("pyint")
    modified = factory.Faker("date_time")
    version = factory.Faker("pyint")
    org = factory.Faker("pystr")
    course = factory.SubFactory(EdxCourseFactory, key=factory.SelfAttribute("..id"))
