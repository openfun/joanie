"""Import data from OpenEdx database"""
import logging
import time
from datetime import datetime
from http import HTTPStatus
from zoneinfo import ZoneInfo

from django.core.files.storage import default_storage
from django.utils.timezone import make_aware as django_make_aware

import requests
from parler.utils import get_language_settings

from joanie.core import models, utils
from joanie.lms_handler.api import detect_lms_from_resource_link
from joanie.lms_handler.backends.openedx import split_course_key
from joanie.lms_handler.edx_imports.edx_database import (
    EDX_DOMAIN,
    EDX_TIME_ZONE,
    OpenEdxDB,
)

# pylint: disable=too-many-statements
# ruff: noqa: PLR0915,SLF001

logger = logging.getLogger(__name__)


def make_date_aware(date: datetime) -> datetime:
    """Make a datetime aware using the OpenEdx timezone"""
    return django_make_aware(date, ZoneInfo(key=EDX_TIME_ZONE))


def format_date(value: datetime) -> str | None:
    """Format a date to isoformat and make it aware"""
    try:
        return make_date_aware(value).isoformat()
    except AttributeError:
        return None


def extract_course_number(course_overview_id):
    """Extract the course number from a course overview id"""
    return utils.normalize_code(split_course_key(course_overview_id)[1])


def download_and_store(filename):
    """Download a file from edx and store it in the default storage"""
    url = f"https://{EDX_DOMAIN}/media/{filename}"
    response = requests.get(url, stream=True, timeout=3)
    logger.info("Downloading %s", url)

    if response.status_code == HTTPStatus.OK:
        with default_storage.open(filename, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    output_file.write(chunk)
    else:
        logger.error("Unable to download file, status code: %s", response.status_code)


def import_universities():
    """Import organizations from OpenEdx universities"""
    logger.info("Getting universities ")
    db = OpenEdxDB()
    universities = db.get_universities()
    logger.info("OK\n")
    for university in universities:
        logger.info("  Import %s: ", university.name)
        _, created = models.Organization.objects.update_or_create(
            code=utils.normalize_code(university.code),
            defaults={
                "title": university.name,
                "logo": university.logo,
            },
        )
        if created:
            logger.info("created\n")
        else:
            logger.info("updated\n")
        download_and_store(university.logo)

    logger.info("Universities import Done\n")


def import_course_runs():
    """Import course runs and courses from OpenEdx course_overviews"""
    logger.info("Getting course runs ")
    db = OpenEdxDB()
    edx_course_overviews = db.get_course_overviews()
    logger.info("OK\n")
    for edx_course_overview in edx_course_overviews:
        logger.info("  Import course run %s: ", edx_course_overview.id)
        # Select LMS from resource link
        resource_link = f"https://{EDX_DOMAIN}/courses/{edx_course_overview.id}/course"
        lms = detect_lms_from_resource_link(resource_link)

        try:
            target_course_run = models.CourseRun.objects.only("pk").get(
                resource_link=resource_link
            )
        except models.CourseRun.DoesNotExist:
            target_course_run = None

        edx_course_run_dict = {
            "resource_link": resource_link,
            "start": format_date(edx_course_overview.start),
            "end": format_date(edx_course_overview.end),
            "enrollment_start": format_date(edx_course_overview.enrollment_start),
            "enrollment_end": format_date(edx_course_overview.enrollment_end),
            "languages": ["fr"],
        }

        if target_course_run:
            # Remove protected fields before update
            cleaned_data = lms.clean_course_run_data(edx_course_run_dict)
            models.CourseRun.objects.filter(pk=target_course_run.pk).update(
                **cleaned_data
            )
            course_run = models.CourseRun.objects.get(pk=target_course_run.pk)
        else:
            course_number = extract_course_number(edx_course_overview.id)
            try:
                course = models.Course.objects.get(code=course_number)
            except models.Course.DoesNotExist:
                course = models.Course.objects.create(
                    created_on=format_date(edx_course_overview.created),
                    code=course_number,
                    title=edx_course_overview.display_name or course_number,
                )
                course.created_on = make_date_aware(edx_course_overview.created)
                course.save()

            # Instantiate a new course run
            course_run = models.CourseRun.objects.create(
                **edx_course_run_dict,
                course=course,
            )
            course_run.created_on = make_date_aware(edx_course_overview.created)
            course_run.save()

        if title := edx_course_overview.display_name:
            # TODO: get language from edx database
            language_code = get_language_settings("fr").get("code")
            course_run.set_current_language(language_code)
            course_run.title = title
        course_run.created_on = make_date_aware(edx_course_overview.created)
        course_run.save()
        logger.info("OK\n")
    logger.info("Course runs import Done\n")


def import_users(batch_size=1000):
    """Import users from OpenEdx auth_user"""
    logger.info("Getting users by batch of %s\n", batch_size)
    db = OpenEdxDB()
    users_count = db.get_users_count()

    for current_user_index in range(0, users_count, batch_size):
        start = current_user_index
        stop = current_user_index + batch_size
        start_time = time.time()
        logger.info("  Processing %s-%s/%s ", start, stop, users_count)
        users = db.get_users(start, stop)
        get_time = time.time()
        logger.info(" %s | ", f"{get_time - start_time:.2f}s")

        build_time = time.time()
        users_to_create = []
        users_to_update = []

        i = 0
        for edx_user in users:
            i += 1
            if not i % 100:
                logger.info(".")

            if edx_user.username == "admin":
                continue
            last_login = format_date(edx_user.last_login)
            date_joined = format_date(edx_user.date_joined)
            try:
                user = models.User.objects.get(username=edx_user.username)
                user.email = edx_user.email
                user.password = edx_user.password
                user.first_name = edx_user.first_name
                user.last_name = edx_user.last_name
                user.is_active = edx_user.is_active
                user.is_staff = edx_user.is_staff
                user.is_superuser = edx_user.is_superuser
                user.date_joined = date_joined
                user.last_login = last_login
                users_to_update.append(user)
            except models.User.DoesNotExist:
                users_to_create.append(
                    models.User(
                        username=edx_user.username,
                        email=edx_user.email,
                        password=edx_user.password,
                        first_name=edx_user.first_name,
                        last_name=edx_user.last_name,
                        is_active=edx_user.is_active,
                        is_staff=edx_user.is_staff,
                        is_superuser=edx_user.is_superuser,
                        date_joined=date_joined,
                        last_login=last_login,
                    )
                )
        build_end_time = time.time()
        logger.info(" %s | ", f"{build_end_time - build_time:.2f}s")
        create_time = time.time()
        users_created = models.User.objects.bulk_create(users_to_create)
        create_end_time = time.time()
        logger.info("Created %s users ", len(users_created))
        logger.info(" %s | ", f"{create_end_time - create_time:.2f}s")

        update_time = time.time()
        users_updated = models.User.objects.bulk_update(
            users_to_update,
            [
                "email",
                "password",
                "first_name",
                "last_name",
                "is_active",
                "is_staff",
                "is_superuser",
                "date_joined",
                "last_login",
            ],
        )
        update_end_time = time.time()
        logger.info("Updated %s users ", users_updated)
        logger.info(" %s | ", f"{update_end_time - update_time:.2f}s")
        logger.info(" %s\n", f"{update_end_time - start_time:.2f}s")
    logger.info("Users import Done\n\n")


def import_enrollments(batch_size=1000):
    """Import enrollments from OpenEdx student_course_enrollment"""
    logger.info("Getting enrollments by batch of %s\n", batch_size)
    db = OpenEdxDB()
    enrollments_count = db.get_enrollments_count()

    last_batch_time = 0
    for current_enrollment_index in range(0, enrollments_count, batch_size):
        enrollments_left = enrollments_count - current_enrollment_index
        eta = enrollments_left / batch_size * last_batch_time / 60 / 60
        logger.info(
            "  %s enrollments left | ETA: %s | ", enrollments_left, f"{eta:.2f}h"
        )

        start = current_enrollment_index
        stop = current_enrollment_index + batch_size
        logger.info("  Processing %s-%s/%s ", start, stop, enrollments_count)
        start_time = time.time()
        enrollments = db.get_enrollments(start, stop)
        get_time = time.time()
        logger.info(" %s | ", f"{get_time - start_time:.2f}s")

        build_time = time.time()
        enrollments_to_create = []
        enrollments_to_update = []

        i = 0
        for edx_enrollment in enrollments:
            i += 1
            if not i % 100:
                logger.info(".")

            try:
                # breakpoint()
                course_run = models.CourseRun.objects.only("pk").get(
                    resource_link__icontains=edx_enrollment.course_id
                )
            except models.CourseRun.DoesNotExist:
                logger.error(
                    "No CourseRun found for course run %s\n",
                    edx_enrollment.course_id,
                )
                continue

            try:
                user_name = edx_enrollment.user.username
                user = models.User.objects.only("pk").get(username=user_name)
            except models.User.DoesNotExist:
                logger.error(
                    "No User found for username %s\n",
                    edx_enrollment.user.username,
                )
                continue

            try:
                enrollment = models.Enrollment.objects.get(
                    course_run=course_run, user=user
                )
                enrollment.is_active = edx_enrollment.is_active
                enrollment.created_on = make_date_aware(edx_enrollment.created)
                enrollments_to_update.append(enrollment)
            except models.Enrollment.DoesNotExist:
                enrollments_to_create.append(
                    models.Enrollment(
                        course_run=course_run,
                        user=user,
                        is_active=edx_enrollment.is_active,
                        created_on=make_date_aware(edx_enrollment.created),
                    )
                )
        build_end_time = time.time()
        logger.info("%s | ", f"{build_end_time - build_time:.2f}s")
        create_time = time.time()

        enrollment_created_on_field = models.Enrollment._meta.get_field("created_on")
        enrollment_created_on_field.auto_now_add = False
        enrollment_created_on_field.editable = True
        enrollments_created = models.Enrollment.objects.bulk_create(
            enrollments_to_create
        )
        create_end_time = time.time()
        logger.info("Created %s enrollments ", len(enrollments_created))
        logger.info(" %s | ", f"{create_end_time - create_time:.2f}s")
        update_time = time.time()
        enrollments_updated = models.Enrollment.objects.bulk_update(
            enrollments_to_update, ["is_active", "created_on"]
        )
        enrollment_created_on_field.auto_now_add = True
        enrollment_created_on_field.editable = False
        update_end_time = time.time()
        logger.info("Updated %s enrollments ", enrollments_updated)
        logger.info(" %s | ", f"{update_end_time - update_time:.2f}s")

        last_batch_time = update_end_time - start_time
        logger.info(" %s\n", f"{last_batch_time:.2f}s")
    logger.info("Enrollments import Done\n\n")
