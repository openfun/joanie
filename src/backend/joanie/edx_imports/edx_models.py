"""Models for the Open edX database."""
import datetime
import decimal
from typing import List, Optional

from sqlalchemy import DECIMAL, DateTime, Double, ForeignKeyConstraint, Index, String
from sqlalchemy.dialects.mysql import INTEGER, TEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models in the database."""


class CourseOverview(Base):
    """Model for the `course_overviews_courseoverview` table."""

    __tablename__ = "course_overviews_courseoverview"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    _location: Mapped[str] = mapped_column(String(255))
    display_number_with_default: Mapped[str] = mapped_column(TEXT)
    display_org_with_default: Mapped[str] = mapped_column(TEXT)
    course_image_url: Mapped[str] = mapped_column(TEXT)
    certificates_show_before_end: Mapped[int] = mapped_column(INTEGER(1))
    has_any_active_web_certificate: Mapped[int] = mapped_column(INTEGER(1))
    cert_name_short: Mapped[str] = mapped_column(TEXT)
    cert_name_long: Mapped[str] = mapped_column(TEXT)
    mobile_available: Mapped[int] = mapped_column(INTEGER(1))
    visible_to_staff_only: Mapped[int] = mapped_column(INTEGER(1))
    _pre_requisite_courses_json: Mapped[str] = mapped_column(TEXT)
    cert_html_view_enabled: Mapped[int] = mapped_column(INTEGER(1))
    invitation_only: Mapped[int] = mapped_column(INTEGER(1))
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    modified: Mapped[datetime.datetime] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(INTEGER(11))
    org: Mapped[str] = mapped_column(TEXT)
    display_name: Mapped[Optional[str]] = mapped_column(TEXT)
    start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    advertised_start: Mapped[Optional[str]] = mapped_column(TEXT)
    facebook_url: Mapped[Optional[str]] = mapped_column(TEXT)
    social_sharing_url: Mapped[Optional[str]] = mapped_column(TEXT)
    end_of_course_survey_url: Mapped[Optional[str]] = mapped_column(TEXT)
    certificates_display_behavior: Mapped[Optional[str]] = mapped_column(TEXT)
    lowest_passing_grade: Mapped[Optional[decimal.Decimal]] = mapped_column(
        DECIMAL(5, 2)
    )
    days_early_for_beta: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Double(asdecimal=True)
    )
    enrollment_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_domain: Mapped[Optional[str]] = mapped_column(TEXT)
    max_student_enrollments_allowed: Mapped[Optional[int]] = mapped_column(INTEGER(11))
    announcement: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    catalog_visibility: Mapped[Optional[str]] = mapped_column(TEXT)
    course_video_url: Mapped[Optional[str]] = mapped_column(TEXT)
    effort: Mapped[Optional[str]] = mapped_column(TEXT)
    short_description: Mapped[Optional[str]] = mapped_column(TEXT)

    course: Mapped["Course"] = relationship(
        "Course", back_populates="course_overviews_courseoverview"
    )


class Course(Base):
    """Model for the `courses_course` table."""

    __tablename__ = "courses_course"
    __table_args__ = (
        ForeignKeyConstraint(
            ["key"],
            ["course_overviews_courseoverview.id"],
            name="key_id_refs_id_45948fcded37bc9d",
        ),
        Index("backoffice_course_key_4f82e863a3ea2609_uniq", "key", unique=True),
        Index("courses_course_199461f6", "start_date"),
        Index("courses_course_2a8f42e8", "level"),
        Index("courses_course_2d978633", "show_in_catalog"),
        Index("courses_course_3fa9fe1c", "score"),
        Index("courses_course_43e08e6f", "show_about_page"),
        Index("courses_course_7dabfeb7", "enrollment_end_date"),
        Index("courses_course_8a7ac9ab", "language"),
        Index("courses_course_b246e1cb", "end_date"),
        Index("courses_course_cf5d0e16", "enrollment_start_date"),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    key: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(255))
    score: Mapped[int] = mapped_column(INTEGER(10))
    is_active: Mapped[int] = mapped_column(INTEGER(1))
    prevent_auto_update: Mapped[int] = mapped_column(INTEGER(1))
    modification_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    title: Mapped[str] = mapped_column(String(255))
    short_description: Mapped[str] = mapped_column(TEXT)
    image_url: Mapped[str] = mapped_column(String(255))
    session_number: Mapped[int] = mapped_column(INTEGER(10))
    university_display_name: Mapped[str] = mapped_column(String(255))
    show_in_catalog: Mapped[int] = mapped_column(INTEGER(1))
    language: Mapped[str] = mapped_column(String(255))
    show_about_page: Mapped[int] = mapped_column(INTEGER(1))
    start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    thumbnails_info: Mapped[Optional[str]] = mapped_column(TEXT)
    enrollment_start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    enrollment_end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    certificate_passing_grade: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Double(asdecimal=True)
    )

    course_overviews_courseoverview: Mapped["CourseOverview"] = relationship(
        "CourseOverview", back_populates="course"
    )
    courses_courseuniversityrelation: Mapped[
        List["CourseUniversityRelation"]
    ] = relationship("CourseUniversityRelation", back_populates="course")


class University(Base):
    """Model for the `universities_university` table."""

    __tablename__ = "universities_university"
    __table_args__ = (
        Index("code", "code", unique=True),
        Index("slug", "slug", unique=True),
        Index("universities_university_28ddafdb", "partnership_level"),
        Index("universities_university_3fa9fe1c", "score"),
        Index("universities_university_52094d6e", "name"),
        Index("universities_university_d7f7fdb2", "is_obsolete"),
        Index("universities_university_eff01f3d", "detail_page_enabled"),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(255))
    logo: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(TEXT)
    detail_page_enabled: Mapped[int] = mapped_column(INTEGER(1))
    score: Mapped[int] = mapped_column(INTEGER(10))
    short_name: Mapped[str] = mapped_column(String(255))
    is_obsolete: Mapped[int] = mapped_column(INTEGER(1))
    prevent_auto_update: Mapped[int] = mapped_column(INTEGER(1))
    partnership_level: Mapped[str] = mapped_column(String(255))
    banner: Mapped[Optional[str]] = mapped_column(String(100))
    certificate_logo: Mapped[Optional[str]] = mapped_column(String(100))

    courses_courseuniversityrelation: Mapped[
        List["CourseUniversityRelation"]
    ] = relationship("CourseUniversityRelation", back_populates="university")


class CourseUniversityRelation(Base):
    """Model for the `courses_courseuniversityrelation` table."""

    __tablename__ = "courses_courseuniversityrelation"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"], name="course_id_refs_id_a613f49d"
        ),
        ForeignKeyConstraint(
            ["university_id"],
            ["universities_university.id"],
            name="university_id_refs_id_666fe783",
        ),
        Index(
            "courses_courseuniversityrel_university_id_45bb9d52955872eb_uniq",
            "university_id",
            "course_id",
            unique=True,
        ),
        Index("courses_courseuniversityrelation_c45f7136", "order"),
        Index("courses_courseuniversityrelation_ca8dbdfe", "university_id"),
        Index("courses_courseuniversityrelation_ff48d8e5", "course_id"),
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    university_id: Mapped[int] = mapped_column(INTEGER(11))
    course_id: Mapped[int] = mapped_column(INTEGER(11))
    order: Mapped[int] = mapped_column(INTEGER(10))

    course: Mapped["Course"] = relationship(
        "Course", back_populates="courses_courseuniversityrelation"
    )
    university: Mapped["University"] = relationship(
        "University", back_populates="courses_courseuniversityrelation"
    )
