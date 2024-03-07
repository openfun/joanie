"""Factory classes for generating fake data for testing."""

import random

import factory
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, registry

from joanie.core import enums
from joanie.edx_imports import edx_models

faker = Faker()
engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
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

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("company")
    slug = factory.Faker("slug")
    code = factory.Faker("pystr")
    logo = factory.Faker("file_path", absolute=False)
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
    course_id = factory.Sequence(lambda n: n)
    university_id = factory.Sequence(lambda n: n)
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


class EdxUserProfileFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX user profiles.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.UserProfile
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: n)
    user_id = factory.Sequence(lambda n: n)
    name = factory.Faker("name")
    location = factory.Faker("address")
    meta = factory.Faker("pystr")
    courseware = factory.Faker("pystr")
    allow_certificate = True

    # pylint: disable=no-self-use
    @factory.lazy_attribute
    def language(self):
        """
        Pick a random language from the complete list of Django supported languages.
        """
        return random.choice(enums.ALL_LANGUAGES)[0]  # noqa: S311


class EdxUserPreferenceFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX user preferences.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.UserPreference
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: n)
    user_id = factory.Sequence(lambda n: n)

    # pylint: disable=no-self-use
    @factory.lazy_attribute
    def key(self):
        """
        Pick a random key from the complete list of Open edX user preferences.
        """
        return ["account_privacy", "dark-lang", "pref-lang"][self.id % 3]

    # pylint: disable=no-self-use
    @factory.lazy_attribute
    def value(self):
        """
        Pick a random language from the complete list of Django supported languages.
        """
        if self.key == "account_privacy":
            return random.choice(["private", "all_users"])  # noqa: S311

        return random.choice(enums.ALL_LANGUAGES)[0]  # noqa: S311


class EdxUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX users.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.User
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: n)
    username = factory.Sequence(lambda n: f"{faker.user_name()}{n}")
    password = factory.Faker("password")
    email = factory.Faker("email")
    first_name = ""
    last_name = ""
    is_active = True
    is_staff = False
    is_superuser = False
    date_joined = factory.Faker("date_time")
    last_login = factory.Faker("date_time")
    auth_userprofile = factory.SubFactory(
        EdxUserProfileFactory, user_id=factory.SelfAttribute("..id")
    )
    user_api_userpreference = factory.RelatedFactoryList(
        EdxUserPreferenceFactory, "user", size=3, user_id=factory.SelfAttribute("..id")
    )


class EdxEnrollmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX enrollments.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.CourseEnrollment
        sqlalchemy_session = session

    user_id = factory.Sequence(lambda n: n)
    user = factory.SubFactory(EdxUserFactory, id=factory.SelfAttribute("..user_id"))
    course_id = factory.Sequence(lambda n: f"course-v1:edX+{faker.pystr()}+{n}")
    created = factory.Faker("date_time")
    is_active = True
    mode = factory.Faker("pystr")


class EdxGeneratedCertificateFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Factory for generating fake Open edX generated certificates.
    """

    class Meta:
        """Factory configuration."""

        model = edx_models.GeneratedCertificate
        sqlalchemy_session = session

    id = factory.Sequence(lambda n: n)
    user_id = factory.Sequence(lambda n: n)
    user = factory.SubFactory(EdxUserFactory, id=factory.SelfAttribute("..user_id"))
    course_id = factory.Sequence(lambda n: f"course-v1:edX+{faker.pystr()}+{n}")
    download_url = factory.Faker("uri")
    grade = factory.Faker("pystr")
    key = factory.Faker("pystr")
    distinction = factory.Faker("pyint")
    status = random.choice(("downloadable", "notpassing", "unavailable"))  # noqa: S311
    verify_uuid = factory.Faker("uuid4")
    download_uuid = factory.Faker("uuid4")
    name = factory.Faker("name")
    created_date = factory.Faker("date_time")
    modified_date = factory.Faker("date_time")
    error_reason = factory.Faker("pystr")
    mode = random.choice(("verified", "honor"))  # noqa: S311


class EdxMongoSignatoryFactory(factory.Factory):
    """
    Factory for generating fake Open edX mongo signatories.
    """

    class Meta:
        """Factory configuration."""

        abstract = False
        model = dict

    id = factory.Sequence(lambda n: n)
    name = f"{faker.first_name()} {faker.last_name()}, {faker.job()}"
    certificate = factory.Faker("pyint")
    title = factory.Faker("sentence")
    organization = factory.Faker("company")
    signature_image_path = factory.Faker("file_path", absolute=True, depth=4)
